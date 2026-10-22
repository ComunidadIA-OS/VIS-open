"""Métricas de la sesión de control del Congreso, según `docs/metricas.md` (Ivette).

Cada función es pura: DataFrame de eventos → `MetricOutput`, y todas las cifras salen de pandas
(regla 3). El frame debe venir de `metrics.contexto.enriquecer_frame`, que añade `block_role`
(rol del turno) e `is_chair` (la Presidencia, que se excluye de todas las métricas salvo M13).

Siempre se separan mujer / hombre / desconocido (voz sin pista de género) y sin_atribuir (evento
sin voz): esos dos grupos no se reparten entre los otros, se informan aparte (M13).
"""

from __future__ import annotations

import pandas as pd

from contracts import GenderValue
from decision.roles import ROLE_ASK, ROLE_GOV
from metrics.frame import GENDER_ORDER, UNATTRIBUTED, speech, speech_time_by_gender
from metrics.registry import MetricOutput, metric

W, M, UNKNOWN = GenderValue.WOMAN.value, GenderValue.MAN.value, GenderValue.UNKNOWN.value
MAX_UNATTRIBUTED_PCT = 20.0  # % de tiempo sin atribuir a partir del cual se avisa
DRAFT = "pendiente de ajustar a Ivette"  # solo M03 y M04 (commits siguientes)


def _seconds_by_gender(frame: pd.DataFrame) -> dict[str, float]:
    """Segundos por mujer / hombre / desconocido / sin_atribuir."""
    return speech_time_by_gender(frame).set_index("gender")["seconds"].to_dict()


def _without_chair(frame: pd.DataFrame) -> pd.DataFrame:
    """Eventos de habla sin la Presidencia, si está identificada."""
    s = speech(frame)
    if "is_chair" not in s.columns:
        return s
    return s[~s["is_chair"].astype(bool)]


@metric(
    metric_id="M01",
    name="M01 Presencia: personas que intervienen, por género y rol",
    min_speakers_known_gender=1,
    min_known_gender_seconds=0,
)
def presence(frame: pd.DataFrame) -> MetricOutput:
    """Personas distintas (no intervenciones) por género y por rol del turno.

    Una misma persona cuenta una vez por rol: el rol es del turno, no de la voz
    (`metrics/contexto.py`). La Presidencia no suma: no pregunta ni responde.
    """
    s = _without_chair(frame)
    voices = s[s["speaker_id"].notna()].drop_duplicates("speaker_id")
    counts = voices["gender"].value_counts()
    by_gender = {g: int(counts.get(g, 0)) for g in (W, M, UNKNOWN)}
    per_role = {}
    for role in (ROLE_ASK, ROLE_GOV):
        if "block_role" in s.columns:
            part = s[s["speaker_id"].notna() & s["block_role"].eq(role)]
            counts = part.drop_duplicates("speaker_id")["gender"].value_counts()
        else:
            counts = {}
        per_role[role] = {g: int(counts.get(g, 0)) for g in (W, M, UNKNOWN)}
    return MetricOutput(
        value=float(len(voices)),
        details={"por_genero": by_gender, "por_rol_y_genero": per_role},
    )


@metric(
    metric_id="M02",
    name="M02 Tiempo de palabra por género y rol",
    min_speakers_known_gender=4,
    min_known_gender_seconds=300,
)
def speaking_time(frame: pd.DataFrame) -> MetricOutput:
    """% del tiempo atribuido (mujeres + hombres) y minutos por persona.

    El denominador excluye la Presidencia, el género desconocido y el tiempo sin atribuir (§2).
    Es descriptiva: las 2 voces por grupo que pide §4 ter son para *comparar*, y eso lo exige M04.
    El detalle conserva `minutos` y `porcentaje_sobre_total` porque los lee el panel, y añade el
    % sobre el tiempo atribuido y los minutos por persona.
    """
    s = _without_chair(frame)
    sec = _seconds_by_gender(s)
    total = sum(sec.values())
    attributed = sec[W] + sec[M]
    if attributed <= 0:
        return MetricOutput(
            value=0.0, reason="no concluyente: sin tiempo de palabra con género conocido"
        )
    people = s[s["speaker_id"].notna()].drop_duplicates("speaker_id")["gender"].value_counts()
    minutes = {g: round(sec[g] / 60, 2) for g in GENDER_ORDER}
    return MetricOutput(
        value=round(100 * sec[W] / attributed, 2),
        details={
            "minutos": minutes,
            "porcentaje_sobre_total": {
                g: round(100 * sec[g] / total, 2) if total else 0.0 for g in GENDER_ORDER
            },
            "porcentaje_atribuido": {
                W: round(100 * sec[W] / attributed, 2),
                M: round(100 * sec[M] / attributed, 2),
            },
            "minutos_por_persona": {
                g: round(minutes[g] / int(people[g]), 2) if people.get(g, 0) else None
                for g in GENDER_ORDER
            },
        },
    )


@metric(
    metric_id="M03",
    name=f"M03 Turnos por género ({DRAFT})",
    min_speakers_known_gender=2,
    min_known_gender_seconds=60,
)
def turns(frame: pd.DataFrame) -> MetricOutput:
    """Turnos = rachas consecutivas de eventos de habla de una misma voz; se cuentan por género."""
    s = speech(frame).sort_values(["start_s", "end_s"])
    s = s[s["speaker_id"].notna()]
    run = (s["speaker_id"] != s["speaker_id"].shift()).cumsum()
    per_turn = s.groupby(run).first()
    counts = per_turn["gender"].value_counts().to_dict()
    by = {g: int(counts.get(g, 0)) for g in (W, M, UNKNOWN)}
    return MetricOutput(value=float(sum(by.values())), details={"por_genero": by})


@metric(
    metric_id="M04",
    name=f"M04 Brecha de paridad en el tiempo de palabra ({DRAFT})",
    min_speakers_known_gender=2,
    min_known_gender_seconds=60,
)
def parity_gap(frame: pd.DataFrame) -> MetricOutput:
    """Puntos porcentuales: % del tiempo de mujeres menos % del tiempo de hombres, ambos sobre el
    total de palabra (negativo = hablan menos las mujeres). No decide si es «concluyente»:
    el umbral lo fija Ivette (ver `gap_is_conclusive`)."""
    sec = _seconds_by_gender(frame)
    total = sum(sec.values())
    w, m = (100 * sec[W] / total, 100 * sec[M] / total) if total else (0.0, 0.0)
    unattributed = 100 * (sec[UNKNOWN] + sec[UNATTRIBUTED]) / total if total else 0
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
    name="M13 Tiempo sin atribuir",
    min_speakers_known_gender=0,
    min_known_gender_seconds=0,
)
def unattributed(frame: pd.DataFrame) -> MetricOutput:
    """% del tiempo de voz que no se puede atribuir: desconocido + sin_atribuir (§7).

    Se calcula siempre y no se oculta: es la calidad del dato. Si supera el 20 %, el detalle lo
    marca en `umbral_superado`, pero el resultado sigue siendo válido (no es «no concluyente»).
    """
    sec = _seconds_by_gender(_without_chair(frame))
    total = sum(sec.values())
    unknown_pct = 100 * sec[UNKNOWN] / total if total else 0.0
    unattributed_pct = 100 * sec[UNATTRIBUTED] / total if total else 0.0
    value = unknown_pct + unattributed_pct
    return MetricOutput(
        value=round(value, 2),
        details={
            "genero_desconocido_%": round(unknown_pct, 2),
            "sin_atribuir_%": round(unattributed_pct, 2),
            "umbral_%": MAX_UNATTRIBUTED_PCT,
            "umbral_superado": value > MAX_UNATTRIBUTED_PCT,
        },
    )
