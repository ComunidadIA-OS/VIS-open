"""Contexto parlamentario: bloque de pregunta y rol del turno, a partir de datos sintéticos."""

import pandas as pd

from contracts import (
    AnalysisEvent,
    AnalysisTimeline,
    EventType,
    Provenance,
    Speaker,
)
from metrics.contexto import enriquecer_frame
from metrics.frame import timeline_to_frame

SPEAKERS = ["SPEAKER_00", "SPEAKER_01", "SPEAKER_02", "SPEAKER_03", "SPEAKER_04"]


def timeline(spec: list[tuple[str | None, float, str | None]]) -> AnalysisTimeline:
    """spec = [(speaker_id | None, segundos, texto)], uno tras otro."""
    events, t = [], 0.0
    for i, (speaker_id, secs, text) in enumerate(spec):
        events.append(
            AnalysisEvent(
                event_id=f"e{i}",
                type=EventType.SPEECH,
                start_s=t,
                end_s=t + secs,
                speaker_id=speaker_id,
                text=text,
                provenance=Provenance.OBSERVED,
            )
        )
        t += secs
    return AnalysisTimeline(
        video_id="SINTETICO",
        duration_s=max(t, 1.0),
        speakers=[Speaker(speaker_id=sid) for sid in SPEAKERS],
        events=events,
    )


def two_questions() -> AnalysisTimeline:
    """Dos preguntas con 4 turnos cada una: pregunta, respuesta, réplica y dúplica."""
    return timeline(
        [
            ("SPEAKER_00", 2, "Tiene la palabra la señora diputada."),
            ("SPEAKER_01", 4, "¿Va a subir el salario mínimo?"),
            ("SPEAKER_01", 0.5, "Se lo pregunto en serio."),  # pausa < 1 s: mismo turno
            ("SPEAKER_02", 4.5, "Sí, señoría."),
            ("SPEAKER_01", 3, "No me convence la respuesta."),
            ("SPEAKER_02", 4, "Es lo que hay."),
            ("SPEAKER_00", 2, "Tiene la palabra el señor diputado."),
            ("SPEAKER_03", 4, "¿Y el de vivienda?"),
            ("SPEAKER_04", 5, "También sube."),
            (None, 2, None),  # tiempo sin voz: nunca entra en un bloque
        ]
    )


def enriched() -> pd.DataFrame:
    tl = two_questions()
    return enriquecer_frame(tl, timeline_to_frame(tl))


def test_blocks_and_roles_of_each_turn():
    df = enriched()
    block = [None if pd.isna(v) else int(v) for v in df["block_index"]]
    turn = [None if pd.isna(v) else int(v) for v in df["turn_index"]]
    got = list(zip(block, turn, df["block_role"], strict=True))
    assert got == [
        (1, None, "PRESIDENCIA"),
        (1, 1, "PREGUNTA"),
        (1, 1, "PREGUNTA"),  # fundido con el turno anterior
        (1, 2, "GOBIERNO"),
        (1, 3, "PREGUNTA"),
        (1, 4, "GOBIERNO"),
        (2, None, "PRESIDENCIA"),
        (2, 1, "PREGUNTA"),
        (2, 2, "GOBIERNO"),
        (None, None, None),  # sin voz
    ]


def test_chair_is_marked_also_outside_the_question_blocks():
    # SPEAKER_00 abre la sesión (fuera de bloque) y luego da la palabra dos veces.
    tl = timeline(
        [
            ("SPEAKER_00", 2, "Buenos días, señorías."),
            ("SPEAKER_00", 2, "Tiene la palabra la señora diputada."),
            ("SPEAKER_01", 4, "¿Va a subir el salario mínimo?"),
            ("SPEAKER_02", 4, "Sí, señoría."),
            ("SPEAKER_00", 2, "Tiene la palabra el señor diputado."),
            ("SPEAKER_03", 4, "¿Y el de vivienda?"),
            ("SPEAKER_04", 5, "También sube."),
        ]
    )
    df = enriquecer_frame(tl, timeline_to_frame(tl))
    assert df["is_chair"].tolist() == [True, True, False, False, True, False, False]
    assert df.loc[0, "block_role"] is None or pd.isna(df.loc[0, "block_role"])  # fuera de bloque


def test_turns_per_question_are_the_ones_m03_counts():
    df = enriched()
    turns = df.dropna(subset=["turn_index"]).groupby("block_index")["turn_index"].nunique()
    assert turns.to_dict() == {1: 4, 2: 2}


def test_role_is_per_block_not_per_voice():
    # SPEAKER_01 pregunta en el bloque 1 y responde en el bloque 2
    tl = timeline(
        [
            ("SPEAKER_00", 2, "Tiene la palabra la señora diputada."),
            ("SPEAKER_01", 4, "¿Va a subir el salario mínimo?"),
            ("SPEAKER_02", 4.5, "Sí, señoría."),
            ("SPEAKER_00", 2, "Tiene la palabra el señor diputado."),
            ("SPEAKER_03", 4, "¿Y el de vivienda?"),
            ("SPEAKER_01", 5, "También sube."),  # ahora responde
        ]
    )
    df = enriquecer_frame(tl, timeline_to_frame(tl))
    by_speaker_block = {
        (row.speaker_id, row.block_index): row.block_role for row in df.itertuples()
    }
    assert by_speaker_block[("SPEAKER_01", 1)] == "PREGUNTA"
    assert by_speaker_block[("SPEAKER_01", 2)] == "GOBIERNO"


def test_without_blocks_everything_is_empty():
    tl = timeline([("SPEAKER_01", 4, "Buenos días."), ("SPEAKER_02", 4, "Hola.")])
    df = enriquecer_frame(tl, timeline_to_frame(tl))
    assert df["block_index"].isna().all()
    assert df["turn_index"].isna().all()
    assert df["block_role"].isna().all()
