"""M01, M02 y M13 con datos sintéticos: los casos de Ivette y los límites de cada métrica."""

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
from metrics.congreso import presence, speaking_time, unattributed
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


@pytest.fixture
def draft_frame() -> pd.DataFrame:
    """Mujer 30 + 30 s (dos turnos), hombre 60 s, género desconocido 20 s y 10 s sin voz."""
    return plain_frame(
        [("SPEAKER_00", 30), ("SPEAKER_02", 60), ("SPEAKER_00", 30), ("SPEAKER_05", 20),
         (None, 10)]  # fmt: skip
    )


def test_m03_turns_are_runs_of_the_same_voice(draft_frame):
    r = run_metric("M03", draft_frame)
    assert r.details["por_genero"] == {"mujer": 2, "hombre": 1, "desconocido": 1}
    assert r.value == 4


def test_m04_gap_is_points_women_minus_men_over_total(draft_frame):
    r = run_metric("M04", draft_frame)
    assert r.value == 0.0  # 40 % - 40 %
    assert r.details["sin_atribuir_o_desconocido_%"] == 20.0


def test_only_m03_and_m04_are_still_labelled_pending():
    # M01, M02 y M13 ya siguen docs/metricas.md; M03 y M04 se ajustan en los commits siguientes.
    assert "pendiente" not in run_metric("M02", balanced_questions()).name
    assert "pendiente" in run_metric("M03", plain_frame([("SPEAKER_01", 4)])).name
