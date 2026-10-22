"""M01, M02 (con M02b), M03, M04 y M13 de la sesión de control, según `docs/metricas.md`.

Cada función es pura: DataFrame de eventos → `MetricOutput`, y todas las cifras salen de pandas
(regla 3). El frame debe venir de `metrics.contexto.enriquecer_frame`, que añade `block_role`
(rol del turno) e `is_chair` (la Presidencia, que se excluye de todas las métricas salvo M13).

Siempre se separan mujer / hombre / desconocido (voz sin pista de género) y sin_atribuir (evento
sin voz): esos dos grupos no se reparten entre los otros, se informan aparte (M13).
"""

from __future__ import annotations

import pandas as pd

from contracts import GenderValue
from decision.roles import MERGE_GAP_S, ROLE_ASK, ROLE_GOV
from metrics.frame import GENDER_ORDER, UNATTRIBUTED, speech, speech_time_by_gender
from metrics.registry import MetricOutput, gap_is_conclusive, metric

W, M, UNKNOWN = GenderValue.WOMAN.value, GenderValue.MAN.value, GenderValue.UNKNOWN.value
MAX_UNATTRIBUTED_PCT = 20.0  # % de tiempo sin atribuir a partir del cual se avisa
QUESTION_SECONDS = 150.0  # §4: ~150 s para quien pregunta y ~150 s para quien responde
TOLERANCE_S = 10.0  # §4: la Presidencia deja terminar la frase
MIN_PEOPLE_PER_GROUP = 2  # §4 ter: dos voces por grupo para comparar
TURN_RANGE = (3, 6)  # §4 ter: turnos por pregunta fuera de este rango = revisar las voces
MIN_QUESTIONS = 10  # §4 ter: M04 necesita 10 preguntas válidas para comparar
GAP_THRESHOLD_POINTS = 15.0  # §3: la brecha debe superar 15 puntos


def _seconds_by_gender(frame: pd.DataFrame) -> dict[str, float]:
    """Segundos por mujer / hombre / desconocido / sin_atribuir."""
    return speech_time_by_gender(frame).set_index("gender")["seconds"].to_dict()


def _without_chair(frame: pd.DataFrame) -> pd.DataFrame:
    """Eventos de habla sin la Presidencia, si está identificada."""
    s = speech(frame)
    if "is_chair" not in s.columns:
        return s
    return s[~s["is_chair"].astype(bool)]


def _questions_by_gender(frame: pd.DataFrame) -> dict[str, int]:
    """Preguntas de cada bloque según el género de quien pregunta (primera voz PREGUNTA)."""
    if "block_role" not in frame.columns or "block_index" not in frame.columns:
        return {g: 0 for g in (W, M, UNKNOWN)}
    s = _without_chair(frame)
    s = s[s["speaker_id"].notna() & s["block_index"].notna()]
    s = s[s["block_role"].eq(ROLE_ASK)]
    askers = s.sort_values(["block_index", "start_s"]).drop_duplicates("block_index")
    counts = askers["gender"].value_counts()
    return {g: int(counts.get(g, 0)) for g in (W, M, UNKNOWN)}


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
    metric_id="M02b",
    name="M02b Uso del tiempo asignado por pregunta",
    min_speakers_known_gender=4,
    min_known_gender_seconds=300,
)
def assigned_time_use(frame: pd.DataFrame) -> MetricOutput:
    """% de uso del tiempo de cada persona en cada pregunta (150 s) y excesos (§M02b).

    Se agrupa por persona y pregunta: quien pregunta tiene ~150 s para pregunta + réplica y quien
    responde otros ~150 s para respuesta + dúplica. Se considera exceso pasar de 160 s (150 s más
    10 s de tolerancia). La Presidencia no entra y las voces sin rol no se comparan.
    """
    if "block_role" not in frame.columns:
        return MetricOutput(
            value=0.0, reason="no aplica: no se han detectado bloques de pregunta"
        )
    s = _without_chair(frame)
    s = s[s["speaker_id"].notna() & s["block_index"].notna()]
    s = s[s["block_role"].isin([ROLE_ASK, ROLE_GOV])]
    if s.empty:
        return MetricOutput(
            value=0.0, reason="no aplica: no se han detectado bloques de pregunta"
        )
    people = s.drop_duplicates("speaker_id")["gender"].value_counts()
    short = [f"{g}: {int(people.get(g, 0))}" for g in (W, M)
             if people.get(g, 0) < MIN_PEOPLE_PER_GROUP]  # fmt: skip
    if short:
        return MetricOutput(
            value=0.0,
            reason=f"no concluyente: menos de {MIN_PEOPLE_PER_GROUP} voces por grupo "
            f"({', '.join(short)})",
        )
    units = (
        s.groupby(["block_index", "speaker_id"], as_index=False)
        .agg(gender=("gender", "first"), role=("block_role", "first"),
             seconds=("duration_s", "sum"))  # fmt: skip
    )
    units["use"] = 100 * units["seconds"] / QUESTION_SECONDS
    over = units["seconds"] > QUESTION_SECONDS + TOLERANCE_S
    use = {
        role: {
            g: round(units.loc[(units["role"] == role) & (units["gender"] == g), "use"].mean(), 2)
            if ((units["role"] == role) & (units["gender"] == g)).any()
            else None
            for g in (W, M)
        }
        for role in (ROLE_ASK, ROLE_GOV)
    }
    excess = {
        g: {
            "n": int(over[units["gender"] == g].sum()),
            "intervenciones": int((units["gender"] == g).sum()),
            "porcentaje": round(100 * over[units["gender"] == g].mean(), 2)
            if (units["gender"] == g).any()
            else 0.0,
        }
        for g in (W, M, UNKNOWN)
    }
    return MetricOutput(
        value=round(100 * over.mean(), 2),
        details={
            "uso_medio_%": use,
            "excesos_por_genero": excess,
            "intervenciones": int(len(units)),
            "umbral_exceso_s": QUESTION_SECONDS + TOLERANCE_S,
        },
    )


@metric(
    metric_id="M03",
    name="M03 Turnos por pregunta (control de calidad)",
    min_speakers_known_gender=2,
    min_known_gender_seconds=60,
)
def turns(frame: pd.DataFrame) -> MetricOutput:
    """Turnos por pregunta = turnos sin Presidencia / preguntas válidas (§M03).

    Un turno son intervenciones seguidas de la misma persona con menos de 1 s de pausa. Se esperan
    unos 4 por pregunta y el rango correcto es 3–6; fuera de él se avisa de que hay que revisar la
    separación de voces. Si el orden del día dice cuántas preguntas válidas hay, se puede fijar en
    `frame.attrs["preguntas_validas"]`; si no, se usan los bloques detectados.
    """
    if "block_index" not in frame.columns:
        return MetricOutput(
            value=0.0, reason="no aplica: no se han detectado bloques de pregunta"
        )
    s = _without_chair(frame)
    s = s[s["speaker_id"].notna() & s["block_index"].notna()]
    s = s.sort_values(["block_index", "start_s", "end_s"])
    if s.empty:
        return MetricOutput(
            value=0.0, reason="no aplica: no se han detectado bloques de pregunta"
        )
    new = (
        (s["block_index"] != s["block_index"].shift())
        | (s["speaker_id"] != s["speaker_id"].shift())
        | (s["start_s"] - s["end_s"].shift() >= MERGE_GAP_S)
    )
    per_turn = s.assign(turn=new.cumsum()).groupby("turn", as_index=False).agg(
        gender=("gender", "first"), seconds=("duration_s", "sum")
    )
    questions = int(frame.attrs.get("preguntas_validas") or s["block_index"].nunique())
    counts = per_turn["gender"].value_counts().to_dict()  # fmt: skip
    by = {g: int(counts.get(g, 0)) for g in (W, M, UNKNOWN)}
    value = len(per_turn) / questions
    inside = TURN_RANGE[0] <= value <= TURN_RANGE[1]
    return MetricOutput(
        value=round(value, 2),
        details={
            "turnos": int(len(per_turn)),
            "preguntas": questions,
            "por_genero": by,
            "duracion_media_turno_s": {
                g: round(per_turn.loc[per_turn["gender"] == g, "seconds"].mean(), 2)
                if (per_turn["gender"] == g).any()
                else None
                for g in (W, M, UNKNOWN)
            },
            "rango_correcto": list(TURN_RANGE),
            "dentro_del_rango": inside,
            "aviso": None
            if inside
            else f"fuera del rango {TURN_RANGE[0]}–{TURN_RANGE[1]}: revisar la separación de voces",
        },
    )


@metric(
    metric_id="M04",
    name="M04 Brecha y ratio de paridad",
    min_speakers_known_gender=4,
    min_known_gender_seconds=600,
)
def parity_gap(frame: pd.DataFrame) -> MetricOutput:
    """Brecha de tiempo, ratio de paridad y brecha de preguntas (§M04).

    a) Brecha de tiempo = % de tiempo de las mujeres − % de mujeres entre quienes intervienen.
    b) Ratio = tiempo medio por mujer / tiempo medio por hombre (1 = equidad).
    c) Brecha de preguntas = % de preguntas de mujeres − % de diputadas. El dato externo llega en
       `frame.attrs["porcentaje_diputadas"]` (medida A) y, si está, `["porcentaje_diputadas_b"]`
       (medida B de la legislatura) para comprobar si cambia la conclusión (§4 bis).
    El umbral de 15 puntos no se aplica aquí: lo usa el panel con `gap_is_conclusive`.
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
    short = [
        f"{g}: {int(people.get(g, 0))}"
        for g in (W, M)
        if people.get(g, 0) < MIN_PEOPLE_PER_GROUP
    ]
    if short:
        return MetricOutput(
            value=0.0,
            reason=f"no concluyente: menos de {MIN_PEOPLE_PER_GROUP} voces por grupo "
            f"({', '.join(short)})",
        )
    blocks = int(frame["block_index"].nunique()) if "block_index" in frame.columns else 0
    questions = int(frame.attrs.get("preguntas_validas") or blocks)
    if questions < MIN_QUESTIONS:
        return MetricOutput(
            value=0.0,
            reason=f"no concluyente: menos de {MIN_QUESTIONS} preguntas válidas ({questions})",
        )
    women_time = 100 * sec[W] / attributed
    known = int(people.get(W, 0)) + int(people.get(M, 0))
    women_people = 100 * int(people.get(W, 0)) / known
    mean = {
        g: round(sec[g] / int(people[g]), 2) if people.get(g, 0) else None for g in (W, M)
    }
    ratio = round(mean[W] / mean[M], 2) if mean[M] else None
    unattributed = 100 * (sec[UNKNOWN] + sec[UNATTRIBUTED]) / total
    asked = _questions_by_gender(frame)
    detected = sum(asked.values())
    preguntas = None
    if detected:
        women_asked = 100 * asked[W] / detected
        external = frame.attrs.get("porcentaje_diputadas")
        preguntas = {
            "validas": questions,
            "detectadas": detected,
            "por_mujeres": asked[W],
            "mujeres_%": round(women_asked, 2),
            "diputadas_%": None if external is None else float(external),
            "brecha_puntos": None
            if external is None
            else round(women_asked - float(external), 2),
        }
        external_b = frame.attrs.get("porcentaje_diputadas_b")
        if external is not None and external_b is not None:
            gap_a = women_asked - float(external)
            gap_b = women_asked - float(external_b)
            ok_a, _ = gap_is_conclusive(
                gap_a, threshold=GAP_THRESHOLD_POINTS,
                unattributed_share=unattributed, margin=None,
            )  # fmt: skip
            ok_b, _ = gap_is_conclusive(
                gap_b, threshold=GAP_THRESHOLD_POINTS,
                unattributed_share=unattributed, margin=None,
            )  # fmt: skip
            preguntas["diputadas_b_%"] = float(external_b)
            preguntas["brecha_b_puntos"] = round(gap_b, 2)
            preguntas["cambia_conclusion"] = ok_a != ok_b
    gap = women_time - women_people
    return MetricOutput(
        value=round(gap, 2),
        margin=round(unattributed, 2),
        details={
            "brecha_tiempo_puntos": round(gap, 2),
            "mujeres_tiempo_%": round(women_time, 2),
            "mujeres_personas_%": round(women_people, 2),
            "ratio_tiempo_medio": ratio,
            "tiempo_medio_s": mean,
            "sin_atribuir_o_desconocido_%": round(unattributed, 2),
            "preguntas": preguntas,
            "umbral_puntos": GAP_THRESHOLD_POINTS,
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
