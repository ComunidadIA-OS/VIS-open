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
import unicodedata

from contracts import AnalysisTimeline, EventType
from decision.gender_cues import CueRules, load_rules

_TITLES = (
    "señora|señor|doña|don|señoría|diputada|diputado|senadora|senador|ministra|ministro|"
    "presidenta|presidente|vicepresidenta|vicepresidente|portavoz|secretaria|secretario|"
    "consejera|consejero|alcaldesa|alcalde|concejala|concejal|eurodiputada|eurodiputado|"
    "compañera|compañero|letrada|letrado|directora|director|parlamentaria|parlamentario"
)
_CAP = r"[A-ZÁÉÍÓÚÑÜ][\wÁÉÍÓÚÑÜáéíóúñü'’-]*"
_NOT_TITLE = rf"(?!(?i:(?:{_TITLES}))\b)"
_NAME_RUN = rf"{_NOT_TITLE}{_CAP}(?:\s+(?:(?:de|del|de\s+la|de\s+los|y)\s+)?{_CAP})*"
# Título(s) + nombre; el nombre es lo que se sustituye (grupo «name»).
_AFTER_TITLE = re.compile(rf"(?i:\b(?:{_TITLES})\b\s+)+(?P<name>{_NAME_RUN})")
_AFTER_INTRO = re.compile(rf"(?i:\b(?:me\s+llamo|mi\s+nombre\s+es)\s+)(?P<name>{_NAME_RUN})")


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


def find_names(text: str) -> list[tuple[int, int, str]]:
    """(inicio, fin, nombre) de cada nombre detectado, sin solapes."""
    spans = []
    for rx in (_AFTER_TITLE, _AFTER_INTRO):
        spans += [(m.start("name"), m.end("name"), m.group("name")) for m in rx.finditer(text)]
    spans.sort()
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


def _replace(text: str, registry: dict[str, str]) -> str:
    for start, end, name in reversed(find_names(text)):
        text = text[:start] + _code_for(name, registry, lambda: "Persona ?") + text[end:]
    return text


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
    for ev in speech:
        for _, _, name in find_names(ev.text or ""):
            if not any(k in registry for k in _keys(name)):
                _code_for(name, registry, lambda n=next_extra: f"Persona {n}")
                next_extra += 1
            else:
                _code_for(name, registry, lambda: "Persona ?")

    events = [
        e.model_copy(update={"text": _replace(e.text, registry)}) if e.text else e
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
