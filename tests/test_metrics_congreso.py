"""M01, M02, M02b, M03 y M04 con datos sintéticos: casos de Ivette y límites de cada métrica."""

import pandas as pd
import pytest

from contracts import (
    AnalysisEvent,
    AnalysisTimeline,
    EventType,
    GenderSource,
    GenderValue,
    Provenance,
    Speaker,
)
from metrics.congreso import (
    assigned_time_use,
    parity_gap,
    presence,
    speaking_time,
    turns,
    unattributed,
)
from metrics.contexto import enriquecer_frame
from metrics.frame import GENDER_ORDER, timeline_to_frame
from metrics.registry import run_metric

SPEAKERS = ["SPEAKER_00", "SPEAKER_01", "SPEAKER_02", "SPEAKER_03", "SPEAKER_04", "SPEAKER_05",
            "SPEAKER_06"]  # fmt: skip
GENDERS = {
    "SPEAKER_00": GenderValue.WOMAN,  # la Presidencia
    "SPEAKER_01": GenderValue.WOMAN,
    "SPEAKER_02": GenderValue.MAN,
    "SPEAKER_03": GenderValue.WOMAN,
    "SPEAKER_04": GenderValue.MAN,
    "SPEAKER_06": GenderValue.MAN,
}  # SPEAKER_05 = voz con género desconocido


def _speaker(speaker_id: str) -> Speaker:
    gender = GENDERS.get(speaker_id, GenderValue.UNKNOWN)
    source = GenderSource.UNKNOWN if gender == GenderValue.UNKNOWN else GenderSource.DECLARED
    return Speaker(speaker_id=speaker_id, gender=gender, gender_source=source)


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
        speakers=[_speaker(s) for s in SPEAKERS],
        events=events,
    )


def frame_of(spec: list[tuple[str | None, float, str | None]]) -> pd.DataFrame:
    tl = timeline(spec)
    return enriquecer_frame(tl, timeline_to_frame(tl))


def two_questions() -> pd.DataFrame:
    """Dos preguntas: la misma diputada pregunta en las dos y responde un hombre y una mujer."""
    return frame_of(
        [
            ("SPEAKER_00", 2, "Tiene la palabra la señora diputada."),
            ("SPEAKER_01", 5, "¿Va a subir el salario mínimo?"),
            ("SPEAKER_02", 2.5, "Sí, señoría."),
            ("SPEAKER_00", 2, "Tiene la palabra el señor diputado."),
            ("SPEAKER_01", 5, "¿Y el de vivienda?"),
            ("SPEAKER_03", 2.5, "También sube."),
        ]
    )


def test_m01_three_voices_by_role_and_gender():
    out = presence(two_questions())
    assert out.value == 3.0  # la Presidencia no cuenta
    assert out.details["por_rol_y_genero"] == {
        "PREGUNTA": {"mujer": 1, "hombre": 0, "desconocido": 0},
        "GOBIERNO": {"mujer": 1, "hombre": 1, "desconocido": 0},
    }


def test_m01_counts_people_not_interventions():
    df = frame_of(
        [
            ("SPEAKER_01", 4, "¿Sube el salario mínimo?"),
            ("SPEAKER_02", 4, "Sí."),
            ("SPEAKER_01", 4, "¿Y las pensiones?"),
            ("SPEAKER_02", 4, "También."),
        ]
    )
    out = presence(df)
    assert out.value == 2.0
    assert out.details["por_genero"] == {"mujer": 1, "hombre": 1, "desconocido": 0}


def balanced_questions() -> pd.DataFrame:
    """Dos preguntas de dos diputadas distintas, con un hombre respondiendo en cada una.

    Mujeres 5 + 5 s, hombres 2,5 + 2,5 s y 4 s de la Presidencia (mujer), que no suma.
    """
    return frame_of(
        [
            ("SPEAKER_00", 2, "Tiene la palabra la señora diputada."),
            ("SPEAKER_01", 5, "¿Va a subir el salario mínimo?"),
            ("SPEAKER_02", 2.5, "Sí, señoría."),
            ("SPEAKER_00", 2, "Tiene la palabra la señora diputada."),
            ("SPEAKER_03", 5, "¿Y el de vivienda?"),
            ("SPEAKER_04", 2.5, "También sube."),
        ]
    )


def test_m02_ivette_case_over_attributed_time():
    # Caso de Ivette: 10 s de mujer y 5 s de hombre → 10 / 15 y 5 / 15.
    out = speaking_time(
        frame_of([("SPEAKER_01", 10, "Una mujer."), ("SPEAKER_02", 5, "Un hombre.")])
    )
    assert out.value == pytest.approx(66.67)
    assert out.details["porcentaje_atribuido"] == {"mujer": 66.67, "hombre": 33.33}
    assert out.details["minutos"] == {"mujer": 0.17, "hombre": 0.08, "desconocido": 0.0,
                                      "sin_atribuir": 0.0}  # fmt: skip


def test_m02_does_not_count_the_chair():
    # Mujeres 5 + 5 s, hombres 2,5 + 2,5 s y 4 s de la Presidencia (mujer): si contara, 73,7 %.
    out = speaking_time(balanced_questions())
    assert out.value == pytest.approx(66.67)
    assert out.details["minutos"]["mujer"] == pytest.approx(0.17)


def test_m02_keeps_the_keys_the_panel_reads():
    details = speaking_time(balanced_questions()).details
    assert list(details["minutos"]) == GENDER_ORDER
    assert list(details["porcentaje_sobre_total"]) == GENDER_ORDER
    assert details["porcentaje_sobre_total"]["mujer"] == pytest.approx(66.67)


def test_m02_under_the_minimum_sample_is_not_conclusive():
    result = run_metric("M02", frame_of([("SPEAKER_01", 10, "M."), ("SPEAKER_02", 5, "H.")]))
    assert result.conclusive is False
    assert result.value is None
    assert "muestra insuficiente" in result.reason


def test_m13_unattributed_plus_unknown_over_total():
    # 10 s mujer + 4 s género desconocido + 6 s sin voz = 20 s → (4 + 6) / 20 = 50 %.
    df = frame_of(
        [("SPEAKER_01", 10, "Una mujer."), ("SPEAKER_05", 4, "Voz sin pista."), (None, 6, None)]
    )
    out = unattributed(df)
    assert out.value == pytest.approx(50.0)
    assert out.details["genero_desconocido_%"] == pytest.approx(20.0)
    assert out.details["sin_atribuir_%"] == pytest.approx(30.0)
    assert out.details["umbral_superado"] is True


def test_m13_is_always_shown_even_with_a_tiny_sample():
    result = run_metric("M13", frame_of([("SPEAKER_01", 4, "Hola.")]))
    assert result.conclusive is True
    assert result.value == pytest.approx(0.0)
    assert result.details["umbral_superado"] is False


def plain_frame(spec: list[tuple[str | None, float]]) -> pd.DataFrame:
    """Eventos consecutivos sin texto: M03 y M04 no necesitan el contexto de bloques."""
    events, t = [], 0.0
    for i, (speaker_id, secs) in enumerate(spec):
        events.append(
            AnalysisEvent(
                event_id=f"e{i}",
                type=EventType.SPEECH,
                start_s=t,
                end_s=t + secs,
                speaker_id=speaker_id,
                provenance=Provenance.OBSERVED,
            )
        )
        t += secs
    tl = AnalysisTimeline(
        video_id="SINTETICO",
        duration_s=max(t, 1.0),
        speakers=[_speaker(s) for s in SPEAKERS],
        events=events,
    )
    return timeline_to_frame(tl)


def four_turns_each() -> pd.DataFrame:
    """Dos preguntas con 4 turnos cada una: pregunta, respuesta, réplica y dúplica."""
    return frame_of(
        [
            ("SPEAKER_00", 2, "Tiene la palabra la señora diputada."),
            ("SPEAKER_01", 4, "¿Va a subir el salario mínimo?"),
            ("SPEAKER_01", 0.5, "Se lo pregunto en serio."),  # pausa < 1 s: mismo turno
            ("SPEAKER_02", 5, "Sí, señoría."),
            ("SPEAKER_01", 3.5, "No me convence."),
            ("SPEAKER_02", 4, "Es lo que hay."),
            ("SPEAKER_00", 2, "Tiene la palabra el señor diputado."),
            ("SPEAKER_03", 4, "¿Y el de vivienda?"),
            ("SPEAKER_03", 0.5, "Se lo pregunto otra vez."),
            ("SPEAKER_04", 5, "También sube."),
            ("SPEAKER_03", 3.5, "No me lo creo."),
            ("SPEAKER_04", 4, "Pues es así."),
        ]
    )


def test_m03_ivette_case_four_turns_per_question():
    out = turns(four_turns_each())
    assert out.value == pytest.approx(4.0)
    assert out.details["turnos"] == 8
    assert out.details["preguntas"] == 2
    assert out.details["por_genero"] == {"mujer": 4, "hombre": 4, "desconocido": 0}
    assert out.details["duracion_media_turno_s"]["mujer"] == pytest.approx(4.0)
    assert out.details["duracion_media_turno_s"]["hombre"] == pytest.approx(4.5)
    assert out.details["dentro_del_rango"] is True
    assert out.details["aviso"] is None


def test_m03_out_of_range_is_flagged_but_keeps_the_number():
    out = turns(two_questions())  # 2 turnos por pregunta: falta la réplica
    assert out.value == pytest.approx(2.0)
    assert out.details["dentro_del_rango"] is False
    assert "revisar la separación de voces" in out.details["aviso"]


def test_m03_uses_the_valid_questions_from_the_order_of_the_day():
    df = four_turns_each()
    df.attrs["preguntas_validas"] = 1  # el orden del día solo tenía una pregunta válida
    out = turns(df)
    assert out.details["preguntas"] == 1
    assert out.value == pytest.approx(8.0)


def assigned_time_frame() -> pd.DataFrame:
    """Dos preguntas con réplica y dúplica: 170/100 s de pregunta y 140/150 s de respuesta."""
    return frame_of(
        [
            ("SPEAKER_00", 2, "Tiene la palabra la señora diputada."),
            ("SPEAKER_01", 150, "Pregunta larga."),
            ("SPEAKER_02", 130, "Respuesta."),
            ("SPEAKER_01", 20, "Réplica."),
            ("SPEAKER_02", 10, "Dúplica."),
            ("SPEAKER_00", 2, "Tiene la palabra la señora diputada."),
            ("SPEAKER_03", 80, "Otra pregunta."),
            ("SPEAKER_04", 140, "Otra respuesta."),
            ("SPEAKER_03", 20, "Otra réplica."),
            ("SPEAKER_04", 10, "Otra dúplica."),
        ]
    )


def test_m02b_ivette_case_use_and_excess():
    # P1 170 s → 113,3 % (exceso); P2 140 s → 93,3 % (no); P3 100 s → 66,7 %; P4 150 s → 100 %.
    out = assigned_time_use(assigned_time_frame())
    assert out.details["uso_medio_%"] == {
        "PREGUNTA": {"mujer": pytest.approx(90.0), "hombre": None},
        "GOBIERNO": {"mujer": None, "hombre": pytest.approx(96.67)},
    }
    assert out.details["excesos_por_genero"]["mujer"] == {
        "n": 1, "intervenciones": 2, "porcentaje": 50.0,
    }  # fmt: skip
    assert out.details["excesos_por_genero"]["hombre"]["n"] == 0
    assert out.value == pytest.approx(25.0)  # 1 de 4 intervenciones se pasa
    assert out.details["preguntas_para_media"] == 2
    assert out.details["preguntas_sin_replica"] == []


def test_m02b_marks_questions_without_replica_and_excludes_them_from_mean():
    df = frame_of(
        [
            ("SPEAKER_00", 2, "Tiene la palabra la señora diputada."),
            ("SPEAKER_01", 100, "Pregunta."),
            ("SPEAKER_02", 100, "Respuesta."),
            ("SPEAKER_01", 20, "Réplica."),
            ("SPEAKER_02", 20, "Dúplica."),
            ("SPEAKER_00", 2, "Tiene la palabra la señora diputada."),
            ("SPEAKER_03", 80, "Otra pregunta."),
            ("SPEAKER_04", 80, "Otra respuesta."),
            ("SPEAKER_03", 10, "Otra réplica."),
            ("SPEAKER_04", 10, "Otra dúplica."),
            ("SPEAKER_00", 2, "Tiene la palabra la señora diputada."),
            ("SPEAKER_01", 170, "Pregunta sin réplica."),
            ("SPEAKER_02", 50, "Respuesta sin réplica."),
        ]
    )
    out = assigned_time_use(df)
    assert out.details["uso_medio_%"] == {
        "PREGUNTA": {"mujer": pytest.approx(70.0), "hombre": None},
        "GOBIERNO": {"mujer": None, "hombre": pytest.approx(70.0)},
    }
    assert out.details["preguntas_para_media"] == 2
    assert out.details["preguntas_sin_replica"] == [
        {"bloque": 3, "intervenciones": 2, "voces": 2}
    ]
    assert out.details["excesos_por_genero"]["mujer"]["n"] == 1
    assert out.details["excesos_por_genero"]["mujer"]["intervenciones"] == 3
    assert out.value == pytest.approx(16.67)  # la pregunta sin réplica sí cuenta para el exceso


def test_m02b_ignores_a_short_interjection_when_counting_interventions():
    df = frame_of(
        [
            ("SPEAKER_00", 2, "Tiene la palabra la señora diputada."),
            ("SPEAKER_01", 100, "Pregunta."),
            ("SPEAKER_02", 100, "Respuesta."),
            ("SPEAKER_01", 20, "Réplica."),
            ("SPEAKER_02", 20, "Dúplica."),
            ("SPEAKER_00", 2, "Tiene la palabra la señora diputada."),
            ("SPEAKER_03", 100, "Otra pregunta."),
            ("SPEAKER_04", 100, "Otra respuesta."),
            ("SPEAKER_03", 20, "Otra réplica."),
            ("SPEAKER_05", 2, "Un ruido de dos segundos."),
        ]
    )
    out = assigned_time_use(df)
    assert out.details["preguntas_para_media"] == 1
    assert out.details["preguntas_sin_replica"] == [
        {"bloque": 2, "intervenciones": 3, "voces": 2}
    ]


def test_m02b_needs_two_voices_in_each_group():
    df = frame_of(
        [
            ("SPEAKER_00", 2, "Tiene la palabra la señora diputada."),
            ("SPEAKER_01", 100, "Una mujer."),
            ("SPEAKER_02", 100, "Un hombre."),
            ("SPEAKER_00", 2, "Tiene la palabra el señor diputado."),
            ("SPEAKER_02", 100, "Otro hombre."),
            ("SPEAKER_04", 100, "Y otro."),
            ("SPEAKER_00", 2, "Tiene la palabra el señor diputado."),
            ("SPEAKER_04", 100, "Otra pregunta."),
            ("SPEAKER_06", 100, "Otra respuesta."),
        ]
    )
    out = assigned_time_use(df)
    assert "menos de 2 voces por grupo" in out.reason
    assert "mujer: 1" in out.reason


def test_m02b_and_m03_without_blocks_are_not_conclusive():
    plain = plain_frame([("SPEAKER_01", 100), ("SPEAKER_02", 100)])
    assert "bloques de pregunta" in assigned_time_use(plain).reason
    assert "bloques de pregunta" in turns(plain).reason


def big_parity_frame() -> pd.DataFrame:
    """2 mujeres y 3 hombres (40 % de las personas) con el 30 % del tiempo en mujeres."""
    df = plain_frame(
        [("SPEAKER_01", 180), ("SPEAKER_03", 180), ("SPEAKER_02", 280),
         ("SPEAKER_04", 280), ("SPEAKER_06", 280)]  # fmt: skip
    )
    df.attrs["preguntas_validas"] = 10
    return df


def test_m04_ivette_case_minus_ten_points():
    # 40 % de las personas y 30 % del tiempo → 30 − 40 = −10 puntos.
    df = big_parity_frame()
    out = parity_gap(df)
    assert out.value == pytest.approx(-10.0)
    assert out.details["mujeres_tiempo_%"] == pytest.approx(30.0)
    assert out.details["mujeres_personas_%"] == pytest.approx(40.0)
    assert out.details["ratio_tiempo_medio"] == pytest.approx(0.64)  # 180 / 280
    assert run_metric("M04", df).conclusive is True


def test_m04_needs_two_voices_in_each_group():
    df = plain_frame([("SPEAKER_01", 300), ("SPEAKER_02", 300), ("SPEAKER_04", 300)])
    df.attrs["preguntas_validas"] = 10
    out = parity_gap(df)
    assert "menos de 2 voces por grupo" in out.reason
    assert "mujer: 1" in out.reason


def test_m04_needs_ten_valid_questions():
    df = big_parity_frame()
    df.attrs["preguntas_validas"] = 9
    assert "menos de 10 preguntas válidas" in parity_gap(df).reason


def test_m04_question_gap_with_the_share_of_women_in_the_chamber():
    df = balanced_questions()
    df.attrs.update(preguntas_validas=10, porcentaje_diputadas=45.9)
    q = parity_gap(df).details["preguntas"]
    assert q["detectadas"] == 2 and q["por_mujeres"] == 2
    assert q["mujeres_%"] == pytest.approx(100.0)
    assert q["brecha_puntos"] == pytest.approx(54.1)  # 100 − 45,9
    assert "cambia_conclusion" not in q


def test_m04_question_gap_measures_the_error_between_measures_a_and_b():
    df = balanced_questions()
    df.attrs.update(
        preguntas_validas=10, porcentaje_diputadas=45.9, porcentaje_diputadas_b=42.8
    )
    q = parity_gap(df).details["preguntas"]
    assert q["brecha_b_puntos"] == pytest.approx(57.2)
    assert q["cambia_conclusion"] is False  # con A y con B la brecha supera 15


def test_no_metric_is_labelled_pending():
    frame = plain_frame([("SPEAKER_01", 4)])
    for metric_id in ("M01", "M02", "M02b", "M03", "M04", "M13"):
        assert "pendiente" not in run_metric(metric_id, frame).name
