"""Seudonimización: ningún nombre propio llega a la salida (decisión del 19 oct).

Cada voz es «Persona N» (N por orden de `speaker_id`). En el texto, el nombre que sigue a un
tratamiento («la señora Luna Ortega», «me llamo Luna Ortega») se sustituye por un código:
- si quien presidía daba la palabra («tiene la palabra la señora X»), X es la voz siguiente;
- cualquier otro nombre recibe un código nuevo, estable en todo el vídeo.

La tabla nombre → código vive solo en memoria y nunca se escribe a disco. Límite conocido: solo
se detectan nombres introducidos por un tratamiento o «me llamo»; un nombre suelto, o uno
que el reconocimiento de voz escriba en minúscula, no se detecta. Las salidas siguen siendo
datos de apoyo y deben revisarse antes de publicarse.
"""

from __future__ import annotations

import re
import tomllib
import unicodedata
from functools import lru_cache

from contracts import AnalysisTimeline, EventType
from decision.gender_cues import CUES_DIR, CueRules, load_rules

_TITLES = (
    "señora|señor|doña|don|señoría|diputada|diputado|senadora|senador|ministra|ministro|"
    "presidenta|presidente|vicepresidenta|vicepresidente|portavoz|secretaria|secretario|"
    "consejera|consejero|alcaldesa|alcalde|concejala|concejal|eurodiputada|eurodiputado|"
    "compañera|compañero|letrada|letrado|directora|director"
)
_CAP = r"[A-ZÁÉÍÓÚÑÜ][\wÁÉÍÓÚÑÜáéíóúñü'’-]*"
_NOT_TITLE = rf"(?!(?i:(?:{_TITLES}))\b)(?!Persona\b)"
_NAME_RUN = rf"{_NOT_TITLE}{_CAP}(?:\s+(?:(?:de|del|de\s+la|de\s+los|y)\s+)?{_CAP})*"
# Título(s) + nombre; el nombre es lo que se sustituye (grupo «name»).
_AFTER_TITLE = re.compile(rf"(?i:\b(?:{_TITLES})\b\s+)+(?P<name>{_NAME_RUN})")
_AFTER_INTRO = re.compile(rf"(?i:\b(?:me\s+llamo|mi\s+nombre\s+es)\s+)(?P<name>{_NAME_RUN})")
# Apellido que la transcripción escribe en minúscula tras un tratamiento: «señor sala, usted…».
_LOWER_AFTER_TITLE = re.compile(
    r"(?i:\b(?:señor|señora|don|doña)\s+)(?P<name>[a-záéíóúñü]+)(?=\s*[,.;:?!])"
)
_TRAIL_CODE = re.compile(r"Persona \d+\s*$")  # el nombre ya se sustituyó justo antes
# El trozo acaba esperando un nombre: «…señor» | «Sala, …»; «doña Persona 52» | «Ortega, …».
_NAME_PENDING = re.compile(rf"(?:(?i:\b(?:{_TITLES}))(?:\s+{_CAP})*|Persona \d+),?\s*$")
_JOIN_GAP_S = 2.0  # dos trozos seguidos de la misma voz a menos de esto pueden partir un nombre


_CONNECTORS = {"de", "del", "la", "los", "y"}


def _keys(name: str) -> list[str]:
    """Una clave por palabra del nombre (sin tildes ni mayúsculas): «Olga Reyes» y «Reyes»
    son la misma persona. Límite: dos personas con una palabra común se confunden."""
    return [t for t in _plain(name).split() if t not in _CONNECTORS]


def _code_for(name: str, registry: dict[str, str], new_code) -> str:
    keys = _keys(name)
    code = next((registry[k] for k in keys if k in registry), None) or new_code()
    for k in keys:
        registry.setdefault(k, code)
    return code


@lru_cache
def _keep_words(language: str = "es") -> frozenset[str]:
    with (CUES_DIR / f"{language}.toml").open("rb") as fh:
        words = tomllib.load(fh).get("pseudonymize", {}).get("keep", [])
    return (
        frozenset(t for w in words for t in _low(w).split())
        | frozenset(t for w in _TITLES.split("|") for t in _low(w).split())
        | {"persona"}
    )


@lru_cache
def _common_words(language: str = "es") -> frozenset[str]:
    with (CUES_DIR / f"{language}.toml").open("rb") as fh:
        words = tomllib.load(fh).get("pseudonymize", {}).get("common", [])
    return frozenset(t for w in words for t in _plain(w).split())


def _low(text: str) -> str:
    """Minúsculas conservando tildes: «Cortés» (apellido) no es «Cortes» (institución)."""
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFC", text).lower()))


_CAP_TOKEN = re.compile(_CAP)
_SENTENCE_START = re.compile(r"(?:^|[.?!¿¡:;«\"(–—-])\s*$")


def _strict_spans(text: str, continues: bool = False) -> list[tuple[int, int, str]]:
    """Palabras con mayúscula a mitad de frase que no están en la lista de excepciones.

    A inicio de frase, una palabra cuenta si va seguida de otra candidata («Agustio Itamillasquer
    presenta») o si es la frase entera («Uriarte.») y no es una palabra común («Gracias.»).
    Con `continues`, el texto sigue una frase del trozo anterior: su inicio no es inicio de frase.
    """
    keep = _keep_words()
    common = _common_words()
    spans: list[tuple[int, int, str]] = []
    held: re.Match | None = None  # candidata al inicio de frase, pendiente de la siguiente
    for m in _CAP_TOKEN.finditer(text):
        if _low(m.group()) in keep or (m.group().isupper() and len(m.group()) >= 2):
            held = None  # lista de excepciones o siglas (IVA, PIB, UE): no son nombres
            continue
        before = text[: m.start()]
        if _SENTENCE_START.search(before) and not (continues and not before.strip()):
            alone = text[m.end() : m.end() + 1] in ("", ".", "?", "!")
            if alone and _plain(m.group()).strip() not in common:
                spans.append((m.start(), m.end(), m.group()))
                held = None
            else:
                held = m
            continue
        if held is not None and text[held.end() : m.start()] == " ":
            spans.append((held.start(), m.end(), text[held.start() : m.end()]))
        elif spans and text[spans[-1][1] : m.start()] == " ":
            spans[-1] = (spans[-1][0], m.end(), text[spans[-1][0] : m.end()])
        else:
            spans.append((m.start(), m.end(), m.group()))
        held = None
    return spans


def find_names(
    text: str, strict: bool = False, continues: bool = False
) -> list[tuple[int, int, str]]:
    """(inicio, fin, nombre) de cada nombre detectado, sin solapes.

    Con `strict`, añade cualquier palabra con mayúscula a mitad de frase que no sea una
    institución o lugar conocido (redacta de más a propósito), y el apellido en minúscula tras
    un tratamiento. `continues`: el texto sigue una frase del trozo anterior.
    """
    spans = []
    for rx in (_AFTER_TITLE, _AFTER_INTRO):
        spans += [(m.start("name"), m.end("name"), m.group("name")) for m in rx.finditer(text)]
    if strict:
        spans += [
            (m.start("name"), m.end("name"), m.group("name"))
            for m in _LOWER_AFTER_TITLE.finditer(text)
            if _low(m.group("name")) not in _keep_words()
        ]
        spans += _strict_spans(text, continues)
    spans.sort(key=lambda s: (s[0], -s[1]))  # a igual inicio, gana el nombre más largo
    out: list[tuple[int, int, str]] = []
    for s in spans:
        if not out or s[0] >= out[-1][1]:
            out.append(s)
    return out


def speaker_codes(timeline: AnalysisTimeline) -> dict[str, str]:
    """`SPEAKER_00` → «Persona 1», por orden de speaker_id."""
    return {s.speaker_id: f"Persona {i}" for i, s in enumerate(
        sorted(timeline.speakers, key=lambda s: s.speaker_id), start=1
    )}  # fmt: skip


def _replace(text: str, registry: dict[str, str], continues: bool = False, prefix: str = "") -> str:
    """Sustituye cada nombre por su código. Si el nombre va justo detrás de otro código
    («Persona 52 Ortega», o «doña Persona 52» | «Ortega» en el trozo anterior), es el resto del
    mismo nombre y se quita."""
    for start, end, name in reversed(find_names(text, strict=True, continues=continues)):
        before = text[:start] if text[:start].strip() else prefix + text[:start]
        if _TRAIL_CODE.search(before):
            text = text[:start].rstrip() + text[end:]
        else:
            text = text[:start] + _code_for(name, registry, lambda: "Persona ?") + text[end:]
    return text


def _continues(prev, ev) -> bool:
    """`ev` sigue la frase de `prev`: misma voz, casi sin pausa y `prev` acaba en un tratamiento
    o en un código, a la espera del nombre."""
    return (
        prev is not None
        and bool(prev.speaker_id)
        and prev.speaker_id == ev.speaker_id
        and ev.start_s - prev.end_s <= _JOIN_GAP_S
        and bool(_NAME_PENDING.search(prev.text or ""))
    )


def pseudonymize_timeline(
    timeline: AnalysisTimeline, rules: CueRules | None = None
) -> tuple[AnalysisTimeline, dict[str, str]]:
    """Copia de la línea de tiempo sin nombres, y el mapa voz → «Persona N» (sin nombres)."""
    rules = rules or load_rules("es")
    codes = speaker_codes(timeline)
    registry: dict[str, str] = {}
    next_extra = len(codes) + 1

    speech = sorted(
        (e for e in timeline.events if e.type == EventType.SPEECH and e.text),
        key=lambda e: (e.start_s, e.end_s),
    )
    # 1) nombres con los que se da la palabra → código de la voz siguiente
    for i, ev in enumerate(speech):
        text = ev.text or ""
        if not any(p in " ".join(_plain(text).split()) for p in _floor_phrases(rules)):
            continue
        nxt = next(
            (
                e
                for e in speech[i + 1 :]
                if e.speaker_id and e.speaker_id != ev.speaker_id
                and e.start_s - ev.end_s <= rules.max_gap_s
            ),
            None,
        )  # fmt: skip
        if nxt is not None:
            for _, _, name in find_names(text):
                _code_for(name, registry, lambda c=codes[nxt.speaker_id]: c)
    # 2) el resto de nombres: código nuevo, estable en todo el vídeo
    cont = {
        id(ev) for prev, ev in zip([None, *speech], speech, strict=False) if _continues(prev, ev)
    }
    texts = [(ev.text or "", id(ev) in cont) for ev in speech]
    texts += [(e.text, False) for e in timeline.events if e.text and e.type != EventType.SPEECH]
    texts += [(g.phrase, False) for s in timeline.speakers for g in s.gender_evidence]
    for text, continues in texts:
        for _, _, name in find_names(text, strict=True, continues=continues):
            if not any(k in registry for k in _keys(name)):
                _code_for(name, registry, lambda n=next_extra: f"Persona {n}")
                next_extra += 1
            else:
                _code_for(name, registry, lambda: "Persona ?")

    new_text: dict[int, str] = {}
    for prev, ev in zip([None, *speech], speech, strict=False):
        c = id(ev) in cont
        new_text[id(ev)] = _replace(ev.text, registry, c, new_text[id(prev)] if c else "")
    events = [
        e.model_copy(update={"text": new_text.get(id(e)) or _replace(e.text, registry)})
        if e.text
        else e
        for e in timeline.events
    ]
    speakers = [
        s.model_copy(
            update={
                "name": None,
                "gender_evidence": [
                    ev.model_copy(update={"phrase": _replace(ev.phrase, registry)})
                    for ev in s.gender_evidence
                ],
            }
        )
        for s in timeline.speakers
    ]
    clean = AnalysisTimeline.model_validate(
        timeline.model_copy(update={"events": events, "speakers": speakers}).model_dump()
    )
    return clean, codes


def _plain(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text.lower())
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in plain if not unicodedata.combining(c)))


def _floor_phrases(rules: CueRules) -> list[str]:
    return [" ".join(p) for p in rules.floor_phrases]
