"""Asistente de voz del panel (v0): órdenes habladas, cerradas, con respuestas de plantilla.

Flujo: tu voz -> transcripción (endpoint `/audio/transcriptions` de AI Endpoints, compatible con
OpenAI) -> `parse_command`, que encaja el texto en una lista CERRADA de órdenes -> el panel obedece
y `answer` contesta con una frase de plantilla. Las cifras salen de los datos con código: ningún
modelo escribe un número. Si no entiende la orden, lo dice y ofrece lo que sabe hacer.

Solo se envía a OVH tu voz diciendo la orden (nunca el audio de las sesiones). La clave
(`LLM_API_KEY`) sale del entorno, nunca del repo. Hecho pensando también en quien no puede leer la
pantalla: todo lo que ocurre se dice en voz alta (ver `dashboard/app.py`).
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
import urllib.request
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass

DEFAULT_ASR_MODEL = "whisper-large-v3-turbo"
MAX_AUDIO_BYTES = 4_000_000  # una orden dura segundos; más es un abuso o un error
MAX_TEXT_CHARS = 200  # una orden es corta; el resto se descarta
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f<>{}`$\\]")
SECTIONS = {  # palabra dicha -> ancla de la sección (ver `dashboard/app.py`)
    "analisis de video": "sec-vanalisis",
    "human in the loop": "sec-hitl",
    "validacion": "sec-hitl",
    "validar": "sec-hitl",
    "voces desconocidas": "sec-hitl",
    "metricas": "sec-metricas",
    "audio": "sec-audio",
    "transcripcion": "sec-audio",
    "descargas": "sec-descargas",
    "informe": "sec-descargas",
    "video": "sec-video",
    "reproductor": "sec-video",
}
_UNITS = {
    "cero": 0, "uno": 1, "una": 1, "un": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12,
    "trece": 13, "catorce": 14, "quince": 15, "dieciseis": 16, "diecisiete": 17,
    "dieciocho": 18, "diecinueve": 19, "veinte": 20, "veintiuno": 21, "veintidos": 22,
    "veintitres": 23, "veinticuatro": 24, "veinticinco": 25, "veintiseis": 26,
    "veintisiete": 27, "veintiocho": 28, "veintinueve": 29,
}  # fmt: skip
_TENS = {"treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70,
         "ochenta": 80, "noventa": 90}  # fmt: skip
ACTIONS = (
    "show_session", "go_section", "go_minute", "women_count", "men_count", "gender_time", "gap",
    "summary", "most_spoken", "pending", "hands", "help", "read_transcript", "explain",
    "validate_start", "val_gender", "val_confirm", "val_cancel", "val_skip", "play_cut", "repeat",
)  # fmt: skip


@dataclass(frozen=True)
class Command:
    action: str
    session: str | None = None
    section: str | None = None
    minute: float | None = None  # minutos (con decimales): 3:59 -> 3,98
    gender: str | None = None  # solo en la validación: lo que DICE la anotadora
    topic: str | None = None


def clean_text(text: str) -> str:
    """Entrada no fiable (voz transcrita o texto escrito): sin control ni marcas, y corta."""
    return " ".join(_CONTROL.sub(" ", text or "").split())[:MAX_TEXT_CHARS]


def normalize(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text.lower())
    plain = "".join(c for c in plain if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", plain).split())


def numbers_in(text: str) -> list[int]:
    """Todos los números del texto, en cifras o en palabras («cuarenta y cinco» -> 45)."""
    tokens = normalize(text).split()
    out: list[int] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.isdigit():
            out.append(int(tok))
        elif tok in _TENS:
            unit = _UNITS.get(tokens[i + 2]) if tokens[i + 1 : i + 2] == ["y"] else None
            if unit is not None and 0 < unit < 10:
                out.append(_TENS[tok] + unit)
                i += 2
            else:
                out.append(_TENS[tok])
        elif tok in _UNITS:
            out.append(_UNITS[tok])
        i += 1
    return out


def number_in(text: str) -> int | None:
    nums = numbers_in(text)
    return nums[0] if nums else None


def time_in(text: str) -> float | None:
    """Minutos de «40», «3:59» o «tres cincuenta y nueve» (minuto y, si hay, segundos)."""
    nums = numbers_in(re.split(r"\b(?:sesion|video|dashboard|panel)\b", normalize(text))[0])
    if not nums:
        return None
    seconds = nums[1] if len(nums) > 1 and nums[1] < 60 else 0
    return nums[0] + seconds / 60


def _session_in(norm: str, sessions: list[str]) -> str | None:
    if "ultima" in norm and sessions:
        return sessions[-1]
    if "primera sesion" in norm and sessions:
        return sessions[0]
    for sid in sessions:  # «v004», «v 004»
        num = int(re.sub(r"\D", "", sid) or -1)
        if re.search(rf"\b{sid.lower()}\b", norm) or re.search(rf"\bv ?0*{num}\b", norm):
            return sid
    after = re.split(r"\b(?:sesion|video|dashboard|panel)\b", norm, maxsplit=1)
    n = number_in(after[1]) if len(after) > 1 else None
    if n is not None:
        for sid in sessions:
            digits = re.sub(r"\D", "", sid)
            if digits and int(digits) == n:
                return sid
    return None


GENDER_WORDS = (
    ("mujer", "mujer"), ("femenin", "mujer"), ("hombre", "hombre"), ("varon", "hombre"),
    ("masculin", "hombre"), ("desconocid", "desconocido"), ("no se", "desconocido"),
    ("no lo se", "desconocido"), ("dudo", "desconocido"), ("no estoy segur", "desconocido"),
)  # fmt: skip


def parse_command(text: str, sessions: list[str], state: str | None = None) -> Command | None:
    """Encaja lo dicho en una orden de la lista cerrada, o None si no la entiende.

    `state` es el paso de la validación por voz: None, "gender" (espera mujer/hombre/desconocido)
    o "confirm" (espera confirmo/cancela). Mujer, hombre y confirmo solo valen en su paso.
    """
    norm = normalize(clean_text(text))
    if not norm:
        return None
    session = _session_in(norm, sessions)
    has = lambda *words: any(w in norm for w in words)  # noqa: E731

    if state == "confirm":
        if has("confirmo", "confirmado", "correcto", "adelante", "guarda") or norm in (
            "si",
            "vale",
        ):
            return Command("val_confirm")
        if has("cancela", "no confirmo", "me equivoque") or norm == "no":
            return Command("val_cancel")
    if state in ("gender", "confirm"):
        for word, gender in GENDER_WORDS:
            if re.search(rf"\b{word}", norm):
                return Command("val_gender", gender=gender)
    if has("cancela", "termina la validacion", "dejar de validar", "para la validacion"):
        return Command("val_cancel")
    if has("siguiente", "salta", "pasa al siguiente"):
        return Command("val_skip")
    if has("reproduce", "ponme el corte", "escuchar el corte", "escucha el corte"):
        return Command("play_cut")
    if has("repite", "otra vez", "no te he oido"):
        return Command("repeat")
    if has("empieza", "empezar", "comenzar", "iniciar", "vamos a validar", "quiero validar"):
        if has("valid", "voces", "human"):
            return Command("validate_start", session)
    if has("que puedo decir", "que puedes hacer", "ayuda"):
        return Command("help")
    if "minuto" in norm and has(
        "transcripcion", "que dicen", "que dice", "leeme", "lee ", "lee la"
    ):
        minute = time_in(norm.split("minuto", 1)[1])
        if minute is not None:
            return Command("read_transcript", session, minute=minute)
    if has("explica", "como funciona", "evolucion", "resultados", "metodo"):
        if has("evolucion", "tendencia", "entre sesiones"):
            return Command("explain", session, topic="evolution")
        if has("resultado"):
            return Command("explain", session, topic="results")
        return Command("explain", session, topic="method")
    if has("cuantas mujeres", "numero de mujeres"):
        return Command("women_count", session)
    if has("cuantos hombres", "numero de hombres"):
        return Command("men_count", session)
    if has("brecha"):
        return Command("gap", session)
    if has("quien hablo mas", "quien mas hablo"):
        return Command("most_spoken", session)
    if has("sin confirmar", "pendientes", "cuantas voces faltan", "voces faltan"):
        return Command("pending", session)
    if has("resumen", "resume", "resumeme", "resumir"):
        return Command("summary", session)
    if "primera mano" in norm:
        return Command("go_minute", session, minute=-1.0)  # -1: la primera mano levantada
    if has("manos levantadas", "cuantas manos"):
        return Command("hands", session)
    if has("tiempo de palabra", "cuanto tiempo", "cuanto hablaron", "cuanto hablan"):
        return Command("gender_time", session)
    if "minuto" in norm:
        minute = time_in(norm.split("minuto", 1)[1])
        if minute is not None:
            return Command("go_minute", session, minute=minute)
    for words, anchor in SECTIONS.items():  # orden: lo más específico primero
        if words in norm:
            return Command("go_section", session, section=anchor)
    if session is not None:
        return Command("show_session", session)
    return None


def es_num(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


HELP_MORE = (
    " También: léeme la transcripción del minuto tres cincuenta y nueve; explícame el análisis; "
    "explícame los resultados; explícame la evolución; empieza la validación de voces."
)
HELP = (
    "Puedes decir: enséñame la sesión cuatro; ve a Human in the loop; ve al análisis de vídeo; "
    "cuántas mujeres hablaron; cuál es la brecha; dame el resumen; quién habló más; "
    "cuántas voces faltan por confirmar; cuántas manos levantadas hubo; "
    "lleva el vídeo al minuto cuarenta." + HELP_MORE
)
NOTE = "Datos orientativos: el género solo cuenta cuando está confirmado o sale del texto."


def answer(cmd: Command, session, pending: int | None = None) -> str:
    """Frase de plantilla con cifras calculadas por código (`session`: `data.Session`)."""
    from dashboard.data import gender_time_table, voices_table

    sid = session.session_id
    voices = voices_table(session)
    by_gender = voices["genero"].value_counts().to_dict()
    women, men, unknown = (by_gender.get(g, 0) for g in ("mujer", "hombre", "desconocido"))
    share = dict(
        zip(*(gender_time_table(session)[c] for c in ("gender", "porcentaje")), strict=True)
    )

    def pct(gender: str) -> str:
        return es_num(share.get(gender, 0))

    if cmd.action == "help":
        return HELP
    if cmd.action == "show_session":
        minutes = session.timeline.duration_s / 60
        return f"Sesión {sid}. Dura {minutes:.0f} minutos y tiene {len(voices)} voces."
    if cmd.action == "go_section":
        return "Aquí tienes la sección."
    if cmd.action == "go_minute":
        return (
            "Hecho."
            if cmd.minute is None or cmd.minute >= 0
            else "Llevo el vídeo a la primera mano levantada."
        )
    if cmd.action in ("women_count", "men_count"):
        who, n = ("mujer", women) if cmd.action == "women_count" else ("hombre", men)
        plural = {"mujer": "voces de mujer", "hombre": "voces de hombre"}[who]
        return (
            f"En la sesión {sid} hay {n} {plural}. {unknown} voces no tienen género todavía. {NOTE}"
        )
    if cmd.action == "gender_time":
        return (
            f"Tiempo de palabra en la sesión {sid}: mujeres {pct('mujer')} por ciento, "
            f"hombres {pct('hombre')} por ciento, sin género "
            f"{es_num(share.get('desconocido', 0) + share.get('sin_atribuir', 0))} por ciento. "
            f"{NOTE}"
        )
    if cmd.action == "gap":
        m04 = session.metrics["M04"]
        if not m04.conclusive:
            reason = (m04.reason or "").removeprefix("no concluyente: ")
            return f"La brecha no es concluyente en la sesión {sid}: {reason}."
        gap = es_num(m04.value)
        return f"La brecha en la sesión {sid} es de {gap} puntos, mujeres menos hombres. {NOTE}"
    if cmd.action == "most_spoken":
        top = voices.iloc[0]
        return f"Habló más {top['persona']}, con {es_num(top['minutos'])} minutos."
    if cmd.action == "pending":
        n = unknown if pending is None else pending
        return f"Quedan {n} voces sin confirmar en la sesión {sid}."
    if cmd.action == "hands":
        v = session.video
        if not v:
            return f"La sesión {sid} no tiene análisis de vídeo."
        total = sum(v.get("manos_levantadas_por_zona", {}).values())
        return (
            f"Se han detectado {total} manos levantadas en la sesión {sid}. "
            "En planos amplios se cuenta de menos."
        )
    if cmd.action == "summary":
        duration = session.timeline.duration_s / 60
        return (
            f"Resumen de la sesión {sid}: dura {duration:.0f} minutos, con {len(voices)} voces; "
            f"{women} de mujer, {men} de hombre y {unknown} sin género. Tiempo de palabra: mujeres "
            f"{pct('mujer')} por ciento y hombres {pct('hombre')} por ciento. {NOTE}"
        )
    return "No sé hacer eso. " + HELP


Transport = Callable[[urllib.request.Request], bytes]


def _urlopen(req: urllib.request.Request) -> bytes:
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - URL de la configuración
        return resp.read()


def transcribe(
    audio: bytes,
    env: Mapping[str, str] | None = None,
    transport: Transport = _urlopen,
    filename: str = "orden.wav",
) -> str:
    """Pasa tu voz a texto con el endpoint de transcripción de AI Endpoints (español)."""
    if not audio or len(audio) > MAX_AUDIO_BYTES:
        raise ValueError("audio vacío o demasiado largo para una orden")
    env = os.environ if env is None else env
    base = (env.get("LLM_BASE_URL") or "").rstrip("/")
    if not base:
        raise ValueError("falta LLM_BASE_URL en el .env")
    model = env.get("VOICE_ASR_MODEL") or DEFAULT_ASR_MODEL
    boundary = uuid.uuid4().hex
    fields = {"model": model, "language": "es", "response_format": "json"}
    body = b""
    for name, value in fields.items():
        body += (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'
        ).encode()
    body += (
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
            f'filename="{filename}"\r\nContent-Type: audio/wav\r\n\r\n'
        ).encode()
        + audio
        + f"\r\n--{boundary}--\r\n".encode()
    )
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    if env.get("LLM_API_KEY"):
        headers["Authorization"] = f"Bearer {env['LLM_API_KEY']}"
    req = urllib.request.Request(f"{base}/audio/transcriptions", data=body, headers=headers)
    # lo transcrito es DATO no fiable: solo se usa para encajar una orden cerrada
    return clean_text(str(json.loads(transport(req)).get("text", "")))


METHOD = (
    "Así funciona el análisis. Se saca el audio del vídeo del Congreso. Un modelo de voz lo pasa a "
    "texto y separa las voces. Cuando quien preside da la palabra, por ejemplo «tiene la palabra "
    "la señora tal», esa voz recibe su género por el texto. El género nunca se deduce de la cara "
    "ni del timbre de la voz. Las voces que quedan sin género las valida una persona, y cuenta "
    "cuando dos personas coinciden. Después el código calcula el tiempo de palabra de mujeres y "
    "de hombres; ningún modelo calcula cifras. Si faltan datos o la diferencia no es clara, el "
    "resultado es no concluyente."
)


def speak_time(minutes: float) -> str:
    m, s = divmod(round(minutes * 60), 60)
    return f"{m} minutos y {s} segundos" if s else f"{m} minutos"


def read_transcript(session, minutes: float, max_chars: int = 600) -> str:
    """Lo que se dice desde ese minuto: texto seudonimizado, leído como DATO, nunca ejecutado."""
    from dashboard.data import transcript_turns

    start = minutes * 60
    all_turns = transcript_turns(session)
    first = max((i for i, t in enumerate(all_turns) if t["inicio_s"] <= start), default=0)
    turns = all_turns[first : first + 3]
    if not turns:
        return f"No hay transcripción en el minuto {speak_time(minutes)} de la sesión."
    out = f"Desde {speak_time(minutes)}. "
    for turn in turns:
        out += f"{turn['persona']} dice: {turn['texto']} "
    return out[:max_chars].rstrip() + (
        "… Pídeme «repite» para volver a oírlo." if len(out) > max_chars else ""
    )


def explain_results(session) -> str:
    return answer(Command("summary"), session) + " " + answer(Command("gap"), session)


def explain_evolution(sessions) -> str:
    from dashboard.data import evolution_gender_table

    table = evolution_gender_table(sessions)
    parts = []
    for sid, rows in table.groupby("sesion", sort=False):
        share = dict(zip(rows["gender"], rows["porcentaje"], strict=True))
        parts.append(
            f"{sid}: mujeres {es_num(share.get('mujer', 0))} por ciento, "
            f"hombres {es_num(share.get('hombre', 0))} por ciento"
        )
    caveat = (
        "Con tan pocas sesiones no se pueden sacar tendencias; una sesión con todo desconocido "
        "aún no tiene género asignado."
    )
    return f"Evolución del tiempo de palabra por sesión. {'; '.join(parts)}. {caveat} {NOTE}"


def pending_cuts(session, folder, who: int) -> list[dict]:
    """Cortes por validar de la anotadora `who`: las voces sin confirmar y sin su respuesta."""
    from dashboard.data import annotator_answers, review_cuts, voices_to_review
    from decision.pseudonymize import speaker_codes

    answers = annotator_answers(folder, who)
    ids = [
        r.speaker_id
        for r in voices_to_review(folder)
        if r.speaker_id not in session.confirmed and r.speaker_id not in answers
    ]
    codes = speaker_codes(session.timeline)
    return [
        {**c, "code": codes.get(str(c["speaker_id"]), str(c["speaker_id"]))}
        for c in review_cuts(session, ids)
    ]


def describe_cut(cut: dict, index: int, total: int) -> str:
    from dashboard.data import fmt_time

    text = str(cut["texto"])[:300]
    return (
        f"Corte {index} de {total}, {cut['code']}, de {fmt_time(float(cut['start']))} a "
        f"{fmt_time(float(cut['stop']))}. En este corte dice: {text}. "
        "Di «reproduce el corte» para oírlo. Luego dime: mujer, hombre o desconocido. "
        "Solo tú decides; yo no sugiero el género."
    )
