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
    "summary", "most_spoken", "pending", "hands", "help",
)  # fmt: skip


@dataclass(frozen=True)
class Command:
    action: str
    session: str | None = None
    section: str | None = None
    minute: float | None = None


def clean_text(text: str) -> str:
    """Entrada no fiable (voz transcrita o texto escrito): sin control ni marcas, y corta."""
    return " ".join(_CONTROL.sub(" ", text or "").split())[:MAX_TEXT_CHARS]


def normalize(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text.lower())
    plain = "".join(c for c in plain if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", plain).split())


def number_in(text: str) -> int | None:
    """Primer número del texto, en cifras («40») o en palabras («cuarenta y cinco»)."""
    tokens = normalize(text).split()
    for i, tok in enumerate(tokens):
        if tok.isdigit():
            return int(tok)
        if tok in _TENS:
            if i + 2 < len(tokens) + 1 and tokens[i + 1 : i + 2] == ["y"] and i + 2 < len(tokens):
                unit = _UNITS.get(tokens[i + 2])
                if unit is not None and 0 < unit < 10:
                    return _TENS[tok] + unit
            return _TENS[tok]
        if tok in _UNITS:
            return _UNITS[tok]
    return None


def _session_in(norm: str, sessions: list[str]) -> str | None:
    if "ultima" in norm and sessions:
        return sessions[-1]
    if "primera" in norm and sessions:
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


def parse_command(text: str, sessions: list[str]) -> Command | None:
    """Encaja lo dicho en una orden de la lista cerrada, o None si no la entiende."""
    norm = normalize(clean_text(text))
    if not norm:
        return None
    session = _session_in(norm, sessions)
    has = lambda *words: any(w in norm for w in words)  # noqa: E731

    if has("que puedo decir", "que puedes hacer", "ayuda"):
        return Command("help")
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
        n = number_in(norm.split("minuto", 1)[1])
        if n is not None:
            return Command("go_minute", session, minute=float(n))
    for words, anchor in SECTIONS.items():  # orden: lo más específico primero
        if words in norm:
            return Command("go_section", session, section=anchor)
    if session is not None:
        return Command("show_session", session)
    return None


def es_num(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


HELP = (
    "Puedes decir: enséñame la sesión cuatro; ve a Human in the loop; ve al análisis de vídeo; "
    "cuántas mujeres hablaron; cuál es la brecha; dame el resumen; quién habló más; "
    "cuántas voces faltan por confirmar; cuántas manos levantadas hubo; "
    "lleva el vídeo al minuto cuarenta."
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
