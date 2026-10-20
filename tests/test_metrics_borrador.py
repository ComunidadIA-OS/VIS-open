"""M01-M04 y M13 en BORRADOR (pendientes de Ivette). Casos hechos a mano, datos sintéticos."""

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
from metrics import run_metric, timeline_to_frame

D = GenderSource.DECLARED


def sp(i, g):
    src = GenderSource.UNKNOWN if g == GenderValue.UNKNOWN else D
    return Speaker(speaker_id=f"SPEAKER_0{i}", gender=g, gender_source=src)


def frame(spec, speakers):
    """spec = [(speaker | None, segundos)] consecutivos."""
    events, t = [], 0.0
    for i, (who, secs) in enumerate(spec):
        events.append(
            AnalysisEvent(
                event_id=f"e{i}",
                type=EventType.SPEECH,
                start_s=t,
                end_s=t + secs,
                speaker_id=who,
                provenance=Provenance.OBSERVED,
            )  # fmt: skip
        )
        t += secs
    tl = AnalysisTimeline(
        video_id="SINTETICO", duration_s=max(t, 1), speakers=speakers, events=events
    )
    return timeline_to_frame(tl)


@pytest.fixture
def f():
    # M0: mujer 30+30 (2 turnos), H1: hombre 60 (1 turno), D2: desconocido 20, sin voz 10
    return frame(
        [("SPEAKER_00", 30), ("SPEAKER_01", 60), ("SPEAKER_00", 30)]
        + [("SPEAKER_02", 20), (None, 10)],
        [sp(0, GenderValue.WOMAN), sp(1, GenderValue.MAN), sp(2, GenderValue.UNKNOWN)],
    )  # fmt: skip


def test_m01_presence(f):
    r = run_metric("M01", f)
    assert r.conclusive and r.value == 3
    assert r.details["por_genero"] == {"mujer": 1, "hombre": 1, "desconocido": 1}


def test_m02_speaking_time(f):
    r = run_metric("M02", f)
    assert r.value == pytest.approx(100 * 60 / 120)  # 60 de 120 s con género conocido
    assert r.details["minutos"]["hombre"] == 1.0
    assert r.details["porcentaje_sobre_total"] == {
        "mujer": 40.0, "hombre": 40.0, "desconocido": 13.33, "sin_atribuir": 6.67,
    }  # fmt: skip


def test_m03_turns_are_runs_of_same_voice(f):
    r = run_metric("M03", f)
    assert r.details["por_genero"] == {"mujer": 2, "hombre": 1, "desconocido": 1}
    assert r.value == 4


def test_m04_gap_is_points_women_minus_men_over_total(f):
    r = run_metric("M04", f)
    assert r.value == 0.0  # 40 % - 40 %
    assert r.details["sin_atribuir_o_desconocido_%"] == 20.0
    few_women = frame(
        [("SPEAKER_00", 20), ("SPEAKER_01", 100)],
        [sp(0, GenderValue.WOMAN), sp(1, GenderValue.MAN)],
    )
    assert run_metric("M04", few_women).value == pytest.approx(-66.67)


def test_m13_unattributed_always_computed_even_without_known_gender():
    only_unknown = frame([("SPEAKER_00", 30), (None, 10)], [sp(0, GenderValue.UNKNOWN)])
    r = run_metric("M13", only_unknown)
    assert r.conclusive and r.value == 25.0
    assert r.details == {"sin_atribuir_%": 25.0, "genero_desconocido_%": 75.0}


def test_m02_not_conclusive_with_small_sample():
    small = frame(
        [("SPEAKER_00", 5), ("SPEAKER_01", 5)], [sp(0, GenderValue.WOMAN), sp(1, GenderValue.MAN)]
    )
    r = run_metric("M02", small)
    assert not r.conclusive and r.value is None and "muestra insuficiente" in r.reason


def test_drafts_are_labelled():
    r = run_metric("M13", frame([("SPEAKER_00", 30)], [sp(0, GenderValue.MAN)]))
    assert "BORRADOR" in r.name
