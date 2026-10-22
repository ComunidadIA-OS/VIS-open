"""Contexto parlamentario de cada evento: bloque de pregunta y rol del turno.

`pipeline/analyze.py` no completa el rol de las voces (`decision.roles.assign_roles`), así que el
rol no viene en el `AnalysisTimeline` que usan las métricas. Aquí se recalcula desde la línea de
tiempo, que sí conserva el texto de cada intervención, y se añade al DataFrame sin tocar el
pipeline ni los contratos.

El rol es el del turno dentro de su bloque, no el mayoritario de la voz: la misma persona puede
preguntar en una pregunta y responder en otra (muchos miembros del Gobierno también son
diputados). `PRESIDENCIA` se informa aparte y nunca entra en las comparaciones: `is_chair` marca
todos sus eventos, también los de fuera de los bloques (apertura, cierre).
"""

from __future__ import annotations

import pandas as pd

from contracts import AnalysisTimeline
from decision.roles import ROLE_CHAIR, QuestionBlock, question_blocks

_EPS = 1e-6


def enriquecer_frame(timeline: AnalysisTimeline, frame: pd.DataFrame) -> pd.DataFrame:
    """Copia del frame con el nº de pregunta, el rol del turno y el nº de turno de cada evento.

    `block_index` y `turn_index` son `Int64` (admiten nulos); `block_role` es el rol del turno
    (`PRESIDENCIA`, `PREGUNTA`, `GOBIERNO` o nulo si es otra voz dentro del bloque). Los eventos
    fuera de un bloque de pregunta quedan con esos tres campos a nulo. `is_chair` marca la
    Presidencia en toda la sesión, dentro y fuera de los bloques.
    """
    out = frame.copy()
    out["block_index"] = pd.array([None] * len(out), dtype="Int64")
    out["turn_index"] = pd.array([None] * len(out), dtype="Int64")
    out["block_role"] = pd.array([None] * len(out), dtype="object")
    blocks = question_blocks(timeline)
    out["is_chair"] = False if not blocks else out["speaker_id"].eq(blocks[0].chair)
    for block in blocks:
        _mark_block(out, block)
    return out


def _mark_block(frame: pd.DataFrame, block: QuestionBlock) -> None:
    chair = frame["speaker_id"].eq(block.chair) & _inside(frame, block.start_s, block.end_s)
    frame.loc[chair, "block_index"] = block.index
    frame.loc[chair, "block_role"] = ROLE_CHAIR
    for index, turn in enumerate(block.turns, start=1):
        hit = (
            frame["speaker_id"].eq(turn.speaker_id)
            & (frame["start_s"] >= turn.start_s - _EPS)
            & (frame["end_s"] <= turn.end_s + _EPS)
        )
        frame.loc[hit, "block_index"] = block.index
        frame.loc[hit, "turn_index"] = index
        frame.loc[hit, "block_role"] = block.role_of(turn.speaker_id)


def _inside(frame: pd.DataFrame, start_s: float, end_s: float) -> pd.Series:
    return (frame["start_s"] >= start_s - _EPS) & (frame["end_s"] <= end_s + _EPS)
