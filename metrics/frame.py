"""De `AnalysisTimeline` a DataFrame, y utilidades base de tiempo de palabra.

Todas las cifras salen de aquí con pandas; ningún LLM calcula ni resume números (regla 3).
`desconocido` (voz con género desconocido) y `sin_atribuir` (evento sin voz) se cuentan aparte:
nunca se reparten entre mujer y hombre.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from contracts import AnalysisTimeline, EventType, GenderValue

UNATTRIBUTED = "sin_atribuir"
GENDER_ORDER = [
    GenderValue.WOMAN.value,
    GenderValue.MAN.value,
    GenderValue.UNKNOWN.value,
    UNATTRIBUTED,
]
COLUMNS = [
    "event_id", "type", "start_s", "end_s", "duration_s", "speaker_id",
    "gender", "gender_source", "provenance", "confidence",
]  # fmt: skip


def timeline_to_frame(timeline: AnalysisTimeline) -> pd.DataFrame:
    """Una fila por evento. `gender` = género de la voz, o `sin_atribuir` si no hay voz."""
    speakers = {s.speaker_id: s for s in timeline.speakers}
    rows = []
    for e in timeline.events:
        sp = speakers.get(e.speaker_id) if e.speaker_id else None
        rows.append(
            {
                "event_id": e.event_id,
                "type": e.type.value,
                "start_s": e.start_s,
                "end_s": e.end_s,
                "duration_s": e.end_s - e.start_s,
                "speaker_id": e.speaker_id,
                "gender": sp.gender.value if sp else UNATTRIBUTED,
                "gender_source": sp.gender_source.value if sp else None,
                "provenance": e.provenance.value,
                "confidence": e.confidence,
            }
        )
    return pd.DataFrame(rows, columns=COLUMNS)


def speech(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[frame["type"] == EventType.SPEECH.value]


def speech_time_by_speaker(frame: pd.DataFrame) -> pd.DataFrame:
    """Segundos de palabra por voz (solo eventos con voz). Suma duraciones: no resta solapes."""
    s = speech(frame)
    s = s[s["speaker_id"].notna()]
    return (
        s.groupby(["speaker_id", "gender"], as_index=False)["duration_s"]
        .sum()
        .rename(columns={"duration_s": "seconds"})
        .sort_values("speaker_id", ignore_index=True)
    )


def speech_time_by_gender(frame: pd.DataFrame) -> pd.DataFrame:
    """Segundos y proporción de palabra por mujer / hombre / desconocido / sin_atribuir.

    `share` es sobre el total de palabra, así que desconocido y sin_atribuir se ven siempre.
    """
    seconds = speech(frame).groupby("gender")["duration_s"].sum()
    out = pd.DataFrame({"gender": GENDER_ORDER})
    out["seconds"] = out["gender"].map(seconds).fillna(0.0)
    total = out["seconds"].sum()
    out["share"] = out["seconds"] / total if total > 0 else 0.0
    return out


@dataclass(frozen=True)
class Sample:
    """Tamaño de la muestra, para mostrarlo siempre junto a cualquier resultado."""

    n_events: int
    n_speakers: int
    n_speakers_known_gender: int
    speech_seconds: float
    known_gender_seconds: float
    unattributed_share: float  # (desconocido + sin_atribuir) / total de palabra


def sample_of(frame: pd.DataFrame) -> Sample:
    by_gender = speech_time_by_gender(frame).set_index("gender")["seconds"]
    total = float(by_gender.sum())
    known = float(by_gender[GenderValue.WOMAN.value] + by_gender[GenderValue.MAN.value])
    by_speaker = speech_time_by_speaker(frame)
    known_speakers = by_speaker[by_speaker["gender"].isin([GenderValue.WOMAN, GenderValue.MAN])]
    return Sample(
        n_events=len(speech(frame)),
        n_speakers=len(by_speaker),
        n_speakers_known_gender=len(known_speakers),
        speech_seconds=total,
        known_gender_seconds=known,
        unattributed_share=(total - known) / total if total > 0 else 0.0,
    )
