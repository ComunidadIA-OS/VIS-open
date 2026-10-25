"""Género por pistas del lenguaje de la transcripción, siempre con evidencia.

Nunca se mira la cara, la voz ni el tono. Cada pista guarda frase, minuto, método y confianza.
Una voz queda `desconocido` y va a revisión humana si no tiene pistas, si tiene pistas que se
contradicen o si la mejor pista tiene confianza < 0,7.

Pistas (ver `decision/cues/<idioma>.toml`, donde viven las palabras):
- floor_grant: otra persona da la palabra («tiene la palabra la señora X») → género de la voz
  que habla a continuación.
- self_role: la propia voz dice «soy la diputada / el portavoz».
- self_agreement: concordancia en primera persona («estoy agradecida»).
- floor_grant_same_voice: lo mismo, pero la diarización juntó a la Presidencia con quien habla;
  pista débil (< 0,7): solo sugiere en la revisión.
- as_role: «como diputada…»; pista débil (puede ser un tercero), siempre a revisión.

No implementado (pendiente): leer el tratamiento «señora presidenta» como pista sobre quien preside,
y ligar nombres propios a voces.

Uso: python -m decision.gender_cues timeline.json [--lang es] [--annotator anotadora_1]
Escribe `timeline_genero.json` y `review_genero_<anotadora>.csv` junto al `timeline.json`.
"""

from __future__ import annotations

import argparse
import re
import tomllib
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from contracts import (
    REVIEW_CONFIDENCE_THRESHOLD,
    AnalysisEvent,
    AnalysisTimeline,
    EventType,
    GenderEvidence,
    GenderSource,
    GenderValue,
    ReviewRow,
    write_rows,
)
from pipeline.timeline import build_review_rows

CUES_DIR = Path(__file__).parent / "cues"
PHRASE_MAX_CHARS = 240
MIN_SPLIT_S = 15.0  # una voz nueva debe sumar al menos esto; menos es ruido (p. ej. una cita)
METHODS = (
    "floor_grant", "floor_grant_same_voice", "self_role", "self_agreement", "as_role",
    "chair_address",
)  # fmt: skip
VOICE_JOIN_S = 2.0  # segmentos seguidos de una misma voz: una sola intervención
MIN_OPENINGS_FOR_CHAIR = 2  # la Presidencia da la palabra o anuncia más de una vez


def _tokens(text: str) -> list[str]:
    """Minúsculas, sin tildes ni puntuación: «Señora» y «senora» coinciden."""
    plain = unicodedata.normalize("NFKD", text.lower())
    plain = "".join(c for c in plain if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+", plain)


@dataclass(frozen=True)
class CueRules:
    """Reglas ya normalizadas de un idioma (viene de un TOML)."""

    language: str
    confidence: dict[str, float]
    floor_phrases: list[list[str]]
    question_phrases: list[list[str]]
    chair_announce: list[list[str]]
    address_max: int
    address_fillers: set[str]
    lookahead: int
    max_gap_s: float
    address: dict[GenderValue, set[str]]
    roles: dict[GenderValue, set[str]]
    epicene: set[str]
    articles: dict[GenderValue, set[str]]
    self_verbs: list[list[str]]
    adverbs: set[str]
    adjectives: dict[str, GenderValue]
    self_role_verbs: set[str]
    as_role_words: set[str]


def _norm_set(words: list[str]) -> set[str]:
    return {t for w in words for t in _tokens(w)}


def load_rules(language: str = "es", path: Path | None = None) -> CueRules:
    path = path or CUES_DIR / f"{language}.toml"
    with Path(path).open("rb") as fh:
        raw = tomllib.load(fh)
    w, m = GenderValue.WOMAN, GenderValue.MAN
    adjectives: dict[str, GenderValue] = {}
    for fem, masc in raw["self_reference"]["adjectives"]:
        adjectives[_tokens(fem)[0]] = w
        adjectives[_tokens(masc)[0]] = m
    return CueRules(
        language=raw["language"],
        confidence=dict(raw["confidence"]),
        floor_phrases=[_tokens(p) for p in raw["floor_grant"]["phrases"]],
        question_phrases=[_tokens(p) for p in raw.get("question_start", {}).get("phrases", [])],
        chair_announce=[_tokens(p) for p in raw.get("chair", {}).get("announce_phrases", [])],
        address_max=raw.get("chair", {}).get("address_max_tokens", 0),
        address_fillers=_norm_set(raw.get("chair", {}).get("address_fillers", [])),
        lookahead=raw["floor_grant"]["lookahead_tokens"],
        max_gap_s=raw["floor_grant"]["max_gap_s"],
        address={w: _norm_set(raw["address"]["woman"]), m: _norm_set(raw["address"]["man"])},
        roles={w: _norm_set(raw["roles"]["woman"]), m: _norm_set(raw["roles"]["man"])},
        epicene=_norm_set(raw["roles"]["epicene"]),
        articles={
            w: _norm_set(raw["roles"]["articles_woman"]),
            m: _norm_set(raw["roles"]["articles_man"]),
        },
        self_verbs=[_tokens(v) for v in raw["self_reference"]["verbs"]],
        adverbs=_norm_set(raw["self_reference"]["adverbs"]),
        adjectives=adjectives,
        self_role_verbs=_norm_set(raw["self_reference"]["self_role_verbs"]),
        as_role_words=_norm_set(raw["self_reference"]["as_role_words"]),
    )


@dataclass(frozen=True)
class Cue:
    speaker_id: str
    evidence: GenderEvidence


def _find(tokens: list[str], phrase: list[str], start: int = 0) -> int | None:
    n = len(phrase)
    for i in range(start, len(tokens) - n + 1):
        if tokens[i : i + n] == phrase:
            return i
    return None


def voice_groups(speech: list[AnalysisEvent]) -> list[tuple[str | None, list[AnalysisEvent]]]:
    """Segmentos seguidos de una misma voz (< VOICE_JOIN_S), que se leen como una intervención.

    Whisper corta a veces un anuncio en dos segmentos («Pregunta del | diputado don…»).
    """
    groups: list[tuple[str | None, list[AnalysisEvent]]] = []
    prev = None
    for e in speech:
        if groups and prev.speaker_id == e.speaker_id and e.start_s - prev.end_s < VOICE_JOIN_S:
            groups[-1][1].append(e)
        else:
            groups.append((e.speaker_id, [e]))
        prev = e
    return groups


def _joined(events: list[AnalysisEvent]) -> str:
    return " ".join(e.text or "" for e in events)


def likely_chair(
    groups: list[tuple[str | None, list[AnalysisEvent]]], rules: CueRules
) -> str | None:
    """La voz que más veces da la palabra o anuncia una pregunta, si lo hace al menos dos veces."""
    phrases = rules.floor_phrases + rules.question_phrases

    def opens(events: list[AnalysisEvent]) -> bool:
        tokens = _tokens(_joined(events))  # una vez por intervención, no una por frase
        return any(_find(tokens, p) is not None for p in phrases)

    counts = Counter(voice for voice, events in groups if voice and opens(events))
    if not counts:
        return None
    voice, n = counts.most_common(1)[0]
    return voice if n >= MIN_OPENINGS_FOR_CHAIR else None


def _chair_announcement(tokens: list[str], rules: CueRules) -> GenderValue | None:
    """Género de quien recibe la palabra en un anuncio (texto ya unido de la Presidencia)."""
    for phrase in rules.floor_phrases + rules.chair_announce:
        at = _find(tokens, phrase)
        if at is None:
            continue
        after = tokens[at + len(phrase) : at + len(phrase) + rules.lookahead]
        if gender := _gender_of_window(after, rules):
            return gender
    return None


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"[.!?¡¿]", text) if _tokens(s)]


def _chair_address(text: str, rules: CueRules, first: bool = False) -> GenderValue | None:
    """«…Señora ministra, cuando quiera.»: tratamiento a solas al final (o al principio) del texto.

    «Señora ministra de Transportes, Movilidad…» se lee hasta «de»: el nombre del ministerio
    (seudonimizado como «Persona N») no dice nada del género y alargaría la frase.
    """
    sentences = _sentences(text)
    if not sentences:
        return None
    sentence = _tokens(sentences[0] if first else sentences[-1])
    if "gracias" in sentence:
        return None
    if "de" in sentence:
        sentence = sentence[: sentence.index("de")]
    tokens = [t for t in sentence if t not in rules.address_fillers]
    starts = rules.address[GenderValue.WOMAN] | rules.address[GenderValue.MAN]
    starts |= rules.roles[GenderValue.WOMAN] | rules.roles[GenderValue.MAN]
    if not tokens or len(tokens) > rules.address_max or tokens[0] not in starts:
        return None
    return _gender_of_window(tokens, rules)


def _chair_cues(speech: list[AnalysisEvent], rules: CueRules) -> list[Cue]:
    """Pistas en las intervenciones de la Presidencia para la voz que habla justo después."""
    groups = voice_groups(speech)
    chair = likely_chair(groups, rules)
    cues: list[Cue] = []
    for (voice, events), (nxt, nxt_events) in zip(groups, groups[1:], strict=False):
        if chair is None or voice != chair or nxt in (None, chair):
            continue
        if nxt_events[0].start_s - events[-1].end_s > rules.max_gap_s:
            continue
        text = _joined(events)
        method, gender = "floor_grant", _chair_announcement(_tokens(text), rules)
        if gender is None:
            method, gender = "chair_address", _chair_address(text, rules)
        if gender is None:
            continue
        evidence = GenderEvidence(
            gender=gender,
            method=method,
            phrase=text.strip()[:PHRASE_MAX_CHARS],
            start_s=events[0].start_s,
            event_id=events[0].event_id,
            confidence=rules.confidence[method],
        )
        cues.append(Cue(nxt, evidence))
    return cues + _edge_address_cues(groups, chair, rules)


def _edge_address_cues(groups, chair: str | None, rules: CueRules) -> list[Cue]:
    """El tratamiento de la Presidencia pegado por la diarización a otra voz.

    «Señora ministra.» a solas al final de la voz anterior o al principio de la siguiente se
    refiere a quien habla después. Si la voz anterior es la Presidencia ya lo lee `_chair_cues`;
    y al principio de la voz que sigue a la Presidencia sería quien pregunta dirigiéndose a la
    ministra, así que ese caso no cuenta. Una pista equivocada choca con las demás y deja la voz
    en «desconocido» (revisión), nunca cambia el género.
    """
    cues: list[Cue] = []
    for (voice, events), (nxt, nxt_events) in zip(groups, groups[1:], strict=False):
        if None in (voice, nxt) or chair in (voice, nxt) or voice == nxt:
            continue
        if nxt_events[0].start_s - events[-1].end_s > rules.max_gap_s:
            continue
        for found, text in (
            (_chair_address(_joined(events), rules), _sentences(_joined(events))[-1:]),
            (
                _chair_address(_joined(nxt_events), rules, first=True),
                _sentences(_joined(nxt_events))[:1],
            ),
        ):
            if found is None:
                continue
            evidence = GenderEvidence(
                gender=found,
                method="address_edge",
                phrase=(text[0].strip() if text else "")[:PHRASE_MAX_CHARS],
                start_s=nxt_events[0].start_s,
                event_id=nxt_events[0].event_id,
                confidence=rules.confidence["address_edge"],
            )
            cues.append(Cue(nxt, evidence))
            break
    return cues


def _gender_of_window(tokens: list[str], rules: CueRules) -> GenderValue | None:
    """Género que señala un tramo de palabras; None si no hay señal o si hay señales mezcladas."""
    if "grupo" in tokens:  # «…del Grupo Parlamentario X»: el grupo no dice el género de la persona
        tokens = tokens[: tokens.index("grupo")]
    found: set[GenderValue] = set()
    for i, tok in enumerate(tokens):
        for g in (GenderValue.WOMAN, GenderValue.MAN):
            if tok in rules.address[g] or tok in rules.roles[g]:
                found.add(g)
            if tok in rules.epicene and i > 0 and tokens[i - 1] in rules.articles[g]:
                found.add(g)
    return next(iter(found)) if len(found) == 1 else None


def _role_after(tokens: list[str], i: int, rules: CueRules) -> GenderValue | None:
    """Cargo en las 2 palabras siguientes a tokens[i] («soy la diputada», «soy portavoz» no)."""
    window = tokens[i + 1 : i + 3]
    for g in (GenderValue.WOMAN, GenderValue.MAN):
        if len(window) >= 1 and window[0] in rules.roles[g]:
            return g
        if (
            len(window) >= 2
            and window[0] in rules.articles[g]
            and (window[1] in rules.roles[g] or window[1] in rules.epicene)
        ):
            return g
    return None


def _evidence(
    event: AnalysisEvent, gender: GenderValue, method: str, conf: float
) -> GenderEvidence:
    return GenderEvidence(
        gender=gender,
        method=method,
        phrase=(event.text or "").strip()[:PHRASE_MAX_CHARS],
        start_s=event.start_s,
        event_id=event.event_id,
        confidence=conf,
    )


def _self_cues(event: AnalysisEvent, rules: CueRules) -> list[tuple[GenderValue, str]]:
    """Pistas sobre quien habla, dentro de su propio texto."""
    tokens = _tokens(event.text or "")
    out: list[tuple[GenderValue, str]] = []
    for i, tok in enumerate(tokens):
        if tok in rules.self_role_verbs and (g := _role_after(tokens, i, rules)):
            out.append((g, "self_role"))
        if tok in rules.as_role_words and (g := _role_after(tokens, i, rules)):
            out.append((g, "as_role"))
        for verb in rules.self_verbs:
            if tokens[i : i + len(verb)] != verb:
                continue
            rest = tokens[i + len(verb) :]
            skip = 0
            while skip < len(rest) and rest[skip] in rules.adverbs and skip < 2:
                skip += 1
            if skip < len(rest) and rest[skip] in rules.adjectives:
                out.append((rules.adjectives[rest[skip]], "self_agreement"))
    return out


def extract_cues(timeline: AnalysisTimeline, rules: CueRules) -> list[Cue]:
    speech = sorted(
        (e for e in timeline.events if e.type == EventType.SPEECH and e.text),
        key=lambda e: (e.start_s, e.end_s),
    )
    cues: list[Cue] = []
    for idx, event in enumerate(speech):
        tokens = _tokens(event.text or "")
        # 1) la voz habla de sí misma
        if event.speaker_id is not None:
            for gender, method in _self_cues(event, rules):
                cues.append(
                    Cue(
                        event.speaker_id, _evidence(event, gender, method, rules.confidence[method])
                    )
                )
        # 2) alguien da la palabra: el género es el de la voz siguiente
        for phrase in rules.floor_phrases:
            at = _find(tokens, phrase)
            if at is None:
                continue
            after = tokens[at + len(phrase) : at + len(phrase) + rules.lookahead]
            gender = _gender_of_window(after, rules)
            if gender is None:
                continue
            nxt = next(
                (
                    e
                    for e in speech[idx + 1 :]
                    if e.speaker_id is not None and e.speaker_id != event.speaker_id
                ),
                None,
            )
            if nxt is None or nxt.start_s - event.end_s > rules.max_gap_s:
                # La diarización puede juntar a la Presidencia con quien habla: pista débil
                # sobre la misma voz (< 0,7), solo para la revisión.
                same = next(
                    (
                        e
                        for e in speech[idx + 1 : idx + 2]
                        if event.speaker_id is not None and e.speaker_id == event.speaker_id
                        and e.start_s - event.end_s <= rules.max_gap_s
                    ),
                    None,
                )  # fmt: skip
                if same is not None:
                    conf = rules.confidence.get("floor_grant_same_voice", 0.6)
                    cues.append(
                        Cue(
                            event.speaker_id,  # type: ignore[arg-type]
                            _evidence(event, gender, "floor_grant_same_voice", conf),
                        )
                    )
                    break
                continue
            cues.append(
                Cue(
                    nxt.speaker_id,  # type: ignore[arg-type]
                    _evidence(event, gender, "floor_grant", rules.confidence["floor_grant"]),
                )
            )
            break
    return cues + _chair_cues(speech, rules)


def _floor_gender(event: AnalysisEvent, rules: CueRules) -> GenderValue | None:
    """Género de a quien se da la palabra en este evento («tiene la palabra la señora X»)."""
    tokens = _tokens(event.text or "")
    for phrase in rules.floor_phrases:
        at = _find(tokens, phrase)
        if at is None:
            continue
        after = tokens[at + len(phrase) : at + len(phrase) + rules.lookahead]
        gender = _gender_of_window(after, rules)
        if gender is not None:
            return gender
    return None


def split_on_floor_grant(
    timeline: AnalysisTimeline, rules: CueRules | None = None
) -> AnalysisTimeline:
    """Separa a quien recibe la palabra cuando la diarización lo juntó con quien la da.

    «Tiene la palabra la señora X» (o «el señor X») marca que lo que sigue es de esa persona. Si la
    diarización dejó la frase y lo que viene después en la misma voz, los eventos siguientes, hasta
    la próxima vez que se da la palabra, pasan a una voz nueva (si suman al menos `MIN_SPLIT_S`).
    Así la regla vale igual con voces separadas o fusionadas. Límite: unos segundos de la
    Presidencia justo después de la frase (p. ej. leer el título) pueden quedar en la voz nueva.
    El género lo asigna después `assign_genders` con la pista habitual (`floor_grant`).
    """
    rules = rules or load_rules()
    speech = sorted(
        (e for e in timeline.events if e.type == EventType.SPEECH and e.text and e.speaker_id),
        key=lambda e: (e.start_s, e.end_s),
    )
    next_id = max((int(sp.speaker_id[-2:]) for sp in timeline.speakers), default=-1) + 1
    moved: dict[str, str] = {}
    origin: dict[str, str] = {}
    i = 0
    while i < len(speech) - 1 and next_id <= 99:
        ev, nxt = speech[i], speech[i + 1]
        if (
            _floor_gender(ev, rules) is None
            or nxt.speaker_id != ev.speaker_id
            or nxt.start_s - ev.end_s > rules.max_gap_s
            or _floor_gender(nxt, rules) is not None
        ):
            i += 1
            continue
        j = i + 1
        while (
            j < len(speech)
            and speech[j].speaker_id == ev.speaker_id
            and _floor_gender(speech[j], rules) is None
        ):
            j += 1
        segment = speech[i + 1 : j]
        if sum(e.end_s - e.start_s for e in segment) >= MIN_SPLIT_S:
            new_id = f"SPEAKER_{next_id:02d}"
            next_id += 1
            for e in segment:
                moved[e.event_id] = new_id
            origin[new_id] = ev.speaker_id  # type: ignore[assignment]
        i = j
    if not moved:
        return timeline
    events = [
        e.model_copy(update={"speaker_id": moved[e.event_id]}) if e.event_id in moved else e
        for e in timeline.events
    ]
    seconds: dict[str, float] = defaultdict(float)
    for e in events:
        if e.type == EventType.SPEECH and e.speaker_id:
            seconds[e.speaker_id] += e.end_s - e.start_s
    speakers = [
        sp.model_copy(update={"total_speech_s": round(seconds[sp.speaker_id], 3)})
        if sp.speaker_id in origin.values()
        else sp
        for sp in timeline.speakers
    ]
    speakers += [
        timeline.speakers[0].__class__(speaker_id=new, total_speech_s=round(seconds[new], 3))
        for new in sorted(origin)
    ]
    return timeline.model_copy(update={"events": events, "speakers": speakers})


@dataclass
class GenderAssignment:
    speaker_id: str
    gender: GenderValue = GenderValue.UNKNOWN
    confidence: float | None = None
    evidence: list[GenderEvidence] = field(default_factory=list)
    needs_review: bool = False
    reason: str = ""

    @property
    def source(self) -> GenderSource:
        return (
            GenderSource.UNKNOWN
            if self.gender == GenderValue.UNKNOWN
            else GenderSource.LANGUAGE_CUE
        )

    @property
    def suggestion(self) -> GenderValue | None:
        """Género sugerido aunque no se asigne (pista débil); None si no hay o se contradicen."""
        genders = {e.gender for e in self.evidence}
        return next(iter(genders)) if len(genders) == 1 else None


def assign_genders(
    timeline: AnalysisTimeline, rules: CueRules | None = None
) -> list[GenderAssignment]:
    rules = rules or load_rules()
    by_speaker: dict[str, list[GenderEvidence]] = defaultdict(list)
    for cue in extract_cues(timeline, rules):
        by_speaker[cue.speaker_id].append(cue.evidence)

    result = []
    for sp in timeline.speakers:
        ev = sorted(by_speaker.get(sp.speaker_id, []), key=lambda e: e.start_s)
        a = GenderAssignment(sp.speaker_id, evidence=ev)
        strong = [e for e in ev if e.confidence >= REVIEW_CONFIDENCE_THRESHOLD]
        # una pista débil («como diputado…», que puede hablar de otra persona) no basta para
        # asignar y tampoco anula a las fuertes; se sigue guardando como evidencia
        genders = {e.gender for e in (strong or ev)}
        if not ev:
            a.needs_review, a.reason = True, "sin pistas en el lenguaje"
        elif len(genders) > 1:
            a.needs_review, a.reason = True, "pistas que se contradicen"
        else:
            a.confidence = max(e.confidence for e in ev)
            if a.confidence < REVIEW_CONFIDENCE_THRESHOLD:
                a.needs_review, a.reason = True, "solo hay pistas débiles (confianza < 0,7)"
            else:
                a.gender = next(iter(genders))
        result.append(a)
    return result


def apply_assignments(
    timeline: AnalysisTimeline, assignments: list[GenderAssignment]
) -> AnalysisTimeline:
    """Copia de la línea de tiempo con el género y la evidencia; no pisa un género ya conocido."""
    by_id = {a.speaker_id: a for a in assignments}
    speakers = []
    for sp in timeline.speakers:
        a = by_id.get(sp.speaker_id)
        if a is None or sp.gender != GenderValue.UNKNOWN:
            speakers.append(sp)
            continue
        speakers.append(
            sp.model_copy(
                update={
                    "gender": a.gender,
                    "gender_source": a.source,
                    "gender_evidence": a.evidence,
                }
            )
        )
    return AnalysisTimeline.model_validate(
        timeline.model_copy(update={"speakers": speakers}).model_dump()
    )


def build_gender_review_rows(
    timeline: AnalysisTimeline, assignments: list[GenderAssignment], annotator_id: str
) -> list[ReviewRow]:
    """Filas de revisión solo para las voces con duda; el género lo decide la anotadora."""
    flagged = {a.speaker_id: a for a in assignments if a.needs_review}
    rows = []
    for row in build_review_rows(timeline, annotator_id):
        a = flagged.get(row.speaker_id)
        if a is None:
            continue
        notes = [f"Motivo: {a.reason}."]
        for e in a.evidence[:3]:
            notes.append(
                f"[min {e.minute}] {e.method} → {e.gender.value} ({e.confidence}): «{e.phrase}»"
            )
        rows.append(row.model_copy(update={"notes": " ".join(notes)}))
    return rows


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("timeline", type=Path)
    parser.add_argument("--lang", default="es")
    parser.add_argument("--annotator", default="anotadora_1")
    args = parser.parse_args(argv)

    timeline = AnalysisTimeline.model_validate_json(args.timeline.read_text(encoding="utf-8"))
    assignments = assign_genders(timeline, load_rules(args.lang))
    out_dir = args.timeline.parent
    (out_dir / "timeline_genero.json").write_text(
        apply_assignments(timeline, assignments).model_dump_json(indent=2), encoding="utf-8"
    )
    csv_path = out_dir / f"review_genero_{args.annotator}.csv"
    write_rows(build_gender_review_rows(timeline, assignments, args.annotator), ReviewRow, csv_path)
    print(out_dir / "timeline_genero.json")
    print(csv_path)


if __name__ == "__main__":
    main()
