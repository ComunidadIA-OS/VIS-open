"""Roles y bloques de pregunta de una sesión de control al Gobierno (base de M02b, M06 y M09).

En el bloque de preguntas del Pleno cada pregunta sigue el mismo guion: la Presidencia da la
palabra («tiene la palabra la señora X»), habla quien pregunta, responde un miembro del Gobierno,
y vuelven una réplica y una dúplica. Por eso los roles se deducen del orden de las voces:

- `PRESIDENCIA`: la voz que da la palabra varias veces. Se excluye de las métricas salvo M13.
- `PREGUNTA`: la primera voz que habla después de que la Presidencia dé la palabra.
- `GOBIERNO`: la primera voz distinta que le contesta.

El rol es de cada **intervención** (un bloque), no de cada persona: un ministro que también es
diputado puede preguntar en un bloque y responder en otro. `Speaker.role` guarda el rol que más
veces tiene cada voz y `QuestionBlock` guarda el rol exacto en cada pregunta.

Límites (ver `docs/ROLES_M09.md`): depende de que la diarización separe bien las voces y de que
la Presidencia diga la fórmula de dar la palabra; si no la encuentra, no devuelve bloques. Esta
deducción es del código y se comprueba con el orden del día y el Diario de Sesiones.

Uso: python -m decision.roles data/processed/<sesión>/timeline_genero.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from contracts import AnalysisTimeline, EventType
from decision.gender_cues import CueRules, _find, _tokens, load_rules

ROLE_CHAIR = "PRESIDENCIA"
ROLE_ASK = "PREGUNTA"
ROLE_GOV = "GOBIERNO"
MIN_TURN_S = 1.0  # una voz que habla menos que esto en un bloque es ruido, no un papel
MERGE_GAP_S = 1.0  # intervenciones seguidas de la misma voz a menos de esto son un turno
MIN_GRANTS_FOR_CHAIR = 2  # la Presidencia da la palabra más de una vez
CHAIR_JOIN_S = 2.0  # segmentos seguidos de una misma voz: una sola intervención


@dataclass(frozen=True)
class Turn:
    speaker_id: str
    start_s: float
    end_s: float
    text: str

    @property
    def seconds(self) -> float:
        return self.end_s - self.start_s


@dataclass
class QuestionBlock:
    """Una pregunta: desde que la Presidencia da la palabra hasta que la da de nuevo."""

    index: int  # nº de pregunta en el tramo, desde 1
    chair: str
    start_s: float
    end_s: float
    asker: str | None = None
    answerer: str | None = None
    turns: list[Turn] = field(default_factory=list)  # sin Presidencia, fundidos

    def seconds(self, speaker_id: str) -> float:
        return sum(t.seconds for t in self.turns if t.speaker_id == speaker_id)

    @property
    def asker_text(self) -> str:
        """Lo que dice quien pregunta en el bloque (para que el modelo decida si es pregunta)."""
        return " ".join(t.text for t in self.turns if t.speaker_id == self.asker).strip()

    def role_of(self, speaker_id: str) -> str | None:
        if speaker_id == self.chair:
            return ROLE_CHAIR
        if speaker_id == self.asker:
            return ROLE_ASK
        if speaker_id == self.answerer:
            return ROLE_GOV
        return None


def _speech(timeline: AnalysisTimeline):
    return sorted(
        (e for e in timeline.events if e.type == EventType.SPEECH and e.speaker_id and e.text),
        key=lambda e: (e.start_s, e.end_s),
    )


def _gives_floor(text: str, rules: CueRules) -> bool:
    tokens = _tokens(text)
    return any(_find(tokens, phrase) is not None for phrase in rules.floor_phrases)


def _starts_question(text: str, rules: CueRules) -> bool:
    tokens = _tokens(text)
    return any(_find(tokens, phrase) is not None for phrase in rules.question_phrases)


def find_chair(timeline: AnalysisTimeline, rules: CueRules | None = None) -> str | None:
    """La voz que más veces da la palabra, si lo hace al menos dos veces."""
    rules = rules or load_rules("es")
    grants = Counter(
        voice
        for voice, events in _voice_groups(_speech(timeline))
        if _opening(events, rules, _opens_any)
    )
    if not grants:
        return None
    speaker, n = grants.most_common(1)[0]
    return speaker if n >= MIN_GRANTS_FOR_CHAIR else None


def _merge(turns: list[Turn]) -> list[Turn]:
    out: list[Turn] = []
    for t in turns:
        if out and out[-1].speaker_id == t.speaker_id and t.start_s - out[-1].end_s < MERGE_GAP_S:
            last = out[-1]
            out[-1] = Turn(last.speaker_id, last.start_s, max(last.end_s, t.end_s),
                           f"{last.text} {t.text}")  # fmt: skip
        else:
            out.append(t)
    return out


def _voice_groups(speech: list) -> list[tuple[str, list]]:
    """Segmentos seguidos de una misma voz (< CHAIR_JOIN_S), que se leen como una intervención.

    Whisper corta a veces un anuncio en dos segmentos («Pregunta del | diputado don…»).
    """
    groups: list[tuple[str, list]] = []
    prev = None
    for e in speech:
        if groups and prev.speaker_id == e.speaker_id and e.start_s - prev.end_s < CHAIR_JOIN_S:
            groups[-1][1].append(e)
        else:
            groups.append((e.speaker_id, [e]))
        prev = e
    return groups


def _opening(events: list, rules: CueRules, opens) -> str | None:
    """`event_id` del segmento donde empieza la frase de apertura, si la intervención la tiene."""
    for e in events:
        if opens(e.text or "", rules):
            return e.event_id
    for k in range(len(events) - 1, -1, -1):  # frase partida: empieza en el último segmento posible
        if opens(" ".join(x.text or "" for x in events[k:]), rules):
            return events[k].event_id
    return None


def _opens_any(text: str, rules: CueRules) -> bool:
    return _gives_floor(text, rules) or _starts_question(text, rules)


def question_blocks(
    timeline: AnalysisTimeline, rules: CueRules | None = None
) -> list[QuestionBlock]:
    """Una lista de preguntas, en orden, con quién pregunta y quién responde en cada una."""
    rules = rules or load_rules("es")
    chair = find_chair(timeline, rules)
    if chair is None:
        return []
    # En la sesión de control la pregunta empieza con su anuncio; «tiene la palabra» abre también
    # la réplica. Sin anuncios (otros debates), cada vez que se da la palabra empieza un bloque.
    speech = _speech(timeline)
    groups = [events for voice, events in _voice_groups(speech) if voice == chair]
    announced = any(_opening(events, rules, _starts_question) for events in groups)
    opens = _starts_question if announced else _gives_floor
    starts = {_opening(events, rules, opens) for events in groups} - {None}
    blocks: list[QuestionBlock] = []
    current: QuestionBlock | None = None
    for e in speech:
        if e.speaker_id == chair:
            if e.event_id in starts:
                current = QuestionBlock(index=len(blocks) + 1, chair=chair,
                                        start_s=e.start_s, end_s=e.end_s)  # fmt: skip
                blocks.append(current)
            elif current is not None:
                current.end_s = max(current.end_s, e.end_s)  # la Presidencia corta o ordena
            continue
        if current is None:
            continue
        current.turns.append(Turn(e.speaker_id or "", e.start_s, e.end_s, e.text or ""))
        current.end_s = max(current.end_s, e.end_s)
    for block in blocks:
        block.turns = [t for t in _merge(block.turns)]
        long = [t for t in block.turns if t.seconds >= MIN_TURN_S] or block.turns
        if long:
            block.asker = long[0].speaker_id
            block.answerer = next((t.speaker_id for t in long if t.speaker_id != block.asker), None)
    return blocks


def assign_roles(
    timeline: AnalysisTimeline, blocks: list[QuestionBlock] | None = None
) -> AnalysisTimeline:
    """Copia de la línea de tiempo con `Speaker.role` (el rol que más veces tiene cada voz)."""
    blocks = question_blocks(timeline) if blocks is None else blocks
    roles: dict[str, Counter] = {}
    for b in blocks:
        for sid in {t.speaker_id for t in b.turns} | {b.chair}:
            role = b.role_of(sid)
            if role:
                roles.setdefault(sid, Counter())[role] += 1
    speakers = [
        s.model_copy(update={"role": roles[s.speaker_id].most_common(1)[0][0]})
        if s.speaker_id in roles
        else s
        for s in timeline.speakers
    ]
    return timeline.model_copy(update={"speakers": speakers})


def summary(blocks: list[QuestionBlock]) -> list[dict]:
    return [
        {
            "pregunta": b.index,
            "inicio_s": round(b.start_s, 1),
            "fin_s": round(b.end_s, 1),
            "presidencia": b.chair,
            "pregunta_voz": b.asker,
            "responde_voz": b.answerer,
            "turnos": len(b.turns),
        }
        for b in blocks
    ]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("timeline", type=Path)
    ap.add_argument("--lang", default="es")
    args = ap.parse_args(argv)
    timeline = AnalysisTimeline.model_validate_json(args.timeline.read_text("utf-8"))
    blocks = question_blocks(timeline, load_rules(args.lang))
    out = args.timeline.with_name("bloques_pregunta.json")
    out.write_text(json.dumps(summary(blocks), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{len(blocks)} preguntas; Presidencia: {find_chair(timeline, load_rules(args.lang))}")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
