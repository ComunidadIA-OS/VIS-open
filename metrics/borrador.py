"""BORRADOR de M01, M02, M03, M04 y M13, a partir de las definiciones de una línea de `README.md`.

PENDIENTE DE IVETTE: la definición formal, los mínimos de muestra y los umbrales son suyos. Los
mínimos de aquí (2 voces y 60 s con género conocido) son provisionales, para que el panel y los
tests funcionen. Cada función es pura: DataFrame de eventos → `MetricOutput`. Siempre se separan
mujer / hombre / desconocido (voz con género desconocido) y sin_atribuir (evento sin voz).
"""

from __future__ import annotations

import pandas as pd

from contracts import GenderValue
from metrics.frame import GENDER_ORDER, UNATTRIBUTED, speech, speech_time_by_gender
from metrics.registry import MetricOutput, metric

W, M = GenderValue.WOMAN.value, GenderValue.MAN.value
DRAFT = "BORRADOR pendiente de Ivette"
MIN_VOICES = 2  # provisional
MIN_SECONDS = 60  # provisional


def _by_gender(frame: pd.DataFrame) -> dict[str, float]:
    return speech_time_by_gender(frame).set_index("gender")["seconds"].to_dict()


@metric(
    metric_id="M01",
    name=f"M01 Presencia: personas que intervienen, por género ({DRAFT})",
    min_speakers_known_gender=MIN_VOICES,
    min_known_gender_seconds=MIN_SECONDS,
)
def presence(frame: pd.DataFrame) -> MetricOutput:
    """Número de voces distintas que intervienen, desglosado por género."""
    s = speech(frame)
    voices = s[s["speaker_id"].notna()].drop_duplicates("speaker_id")
    counts = voices["gender"].value_counts().to_dict()
    by = {g: int(counts.get(g, 0)) for g in (W, M, GenderValue.UNKNOWN.value)}
    return MetricOutput(value=float(len(voices)), details={"por_genero": by})


@metric(
    metric_id="M02",
    name=f"M02 Tiempo de palabra por género ({DRAFT})",
    min_speakers_known_gender=MIN_VOICES,
    min_known_gender_seconds=MIN_SECONDS,
)
def speaking_time(frame: pd.DataFrame) -> MetricOutput:
    """Porcentaje del tiempo de palabra de las mujeres sobre mujeres + hombres; el detalle da
    minutos y porcentaje sobre el total para los cuatro grupos."""
    sec = _by_gender(frame)
    known = sec[W] + sec[M]
    total = sum(sec.values())
    return MetricOutput(
        value=round(100 * sec[W] / known, 2) if known else 0.0,
        details={
            "minutos": {g: round(sec[g] / 60, 2) for g in GENDER_ORDER},
            "porcentaje_sobre_total": {
                g: round(100 * sec[g] / total, 2) if total else 0.0 for g in GENDER_ORDER
            },
        },
    )


@metric(
    metric_id="M03",
    name=f"M03 Turnos por género ({DRAFT})",
    min_speakers_known_gender=MIN_VOICES,
    min_known_gender_seconds=MIN_SECONDS,
)
def turns(frame: pd.DataFrame) -> MetricOutput:
    """Turnos = rachas consecutivas de eventos de habla de una misma voz; se cuentan por género."""
    s = speech(frame).sort_values(["start_s", "end_s"])
    s = s[s["speaker_id"].notna()]
    run = (s["speaker_id"] != s["speaker_id"].shift()).cumsum()
    per_turn = s.groupby(run).first()
    counts = per_turn["gender"].value_counts().to_dict()
    by = {g: int(counts.get(g, 0)) for g in (W, M, GenderValue.UNKNOWN.value)}
    return MetricOutput(value=float(sum(by.values())), details={"por_genero": by})


@metric(
    metric_id="M04",
    name=f"M04 Brecha de paridad en el tiempo de palabra ({DRAFT})",
    min_speakers_known_gender=MIN_VOICES,
    min_known_gender_seconds=MIN_SECONDS,
)
def parity_gap(frame: pd.DataFrame) -> MetricOutput:
    """Puntos porcentuales: % del tiempo de mujeres menos % del tiempo de hombres, ambos sobre el
    total de palabra (negativo = hablan menos las mujeres). No decide si es «concluyente»:
    el umbral lo fija Ivette (ver `gap_is_conclusive`)."""
    sec = _by_gender(frame)
    total = sum(sec.values())
    w, m = (100 * sec[W] / total, 100 * sec[M] / total) if total else (0.0, 0.0)
    unattributed = (
        100 * (sec[GenderValue.UNKNOWN.value] + sec[UNATTRIBUTED]) / total if total else 0
    )
    return MetricOutput(
        value=round(w - m, 2),
        details={
            "mujeres_%": round(w, 2),
            "hombres_%": round(m, 2),
            "sin_atribuir_o_desconocido_%": round(unattributed, 2),
        },
    )


@metric(
    metric_id="M13",
    name=f"M13 Tiempo sin atribuir ({DRAFT})",
    min_speakers_known_gender=0,
    min_known_gender_seconds=0,
)
def unattributed(frame: pd.DataFrame) -> MetricOutput:
    """Porcentaje del tiempo de palabra sin voz atribuida; el detalle da también el de voces con
    género desconocido."""
    sec = _by_gender(frame)
    total = sum(sec.values())
    pct = lambda g: round(100 * sec[g] / total, 2) if total else 0.0  # noqa: E731
    return MetricOutput(
        value=pct(UNATTRIBUTED),
        details={"sin_atribuir_%": pct(UNATTRIBUTED), "genero_desconocido_%": pct("desconocido")},
    )
