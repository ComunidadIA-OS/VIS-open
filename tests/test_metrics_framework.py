"""Marco de métricas. Datos sintéticos; la métrica X00_EJEMPLO no es una métrica real."""

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
from metrics import (
    gap_is_conclusive,
    get_metric,
    list_metrics,
    metric,
    run_metric,
    sample_of,
    speech_time_by_gender,
    speech_time_by_speaker,
    timeline_to_frame,
)
from metrics.registry import MetricOutput

D = GenderSource.DECLARED


def timeline(spec: list[tuple[str | None, float]], speakers: list[Speaker]) -> AnalysisTimeline:
    """spec = [(speaker_id | None, segundos)], uno tras otro."""
    events, t = [], 0.0
    for i, (sp, secs) in enumerate(spec):
        events.append(
            AnalysisEvent(
                event_id=f"e{i}",
                type=EventType.SPEECH,
                start_s=t,
                end_s=t + secs,
                speaker_id=sp,
                provenance=Provenance.OBSERVED,
            )  # fmt: skip
        )
        t += secs
    return AnalysisTimeline(
        video_id="SINTETICO", duration_s=max(t, 1.0), speakers=speakers, events=events
    )


def woman(i):
    return Speaker(speaker_id=f"SPEAKER_0{i}", gender=GenderValue.WOMAN, gender_source=D)


def man(i):
    return Speaker(speaker_id=f"SPEAKER_0{i}", gender=GenderValue.MAN, gender_source=D)


def unknown(i):
    return Speaker(speaker_id=f"SPEAKER_0{i}")


@pytest.fixture
def mixed():
    # mujer 30 s, hombre 60 s, voz desconocida 10 s, 20 s sin voz
    return timeline(
        [("SPEAKER_00", 30), ("SPEAKER_01", 60), ("SPEAKER_02", 10), (None, 20)],
        [woman(0), man(1), unknown(2)],
    )


def test_frame_has_one_row_per_event_with_gender(mixed):
    df = timeline_to_frame(mixed)
    assert len(df) == 4
    assert list(df["gender"]) == ["mujer", "hombre", "desconocido", "sin_atribuir"]


def test_unknown_and_unattributed_are_kept_apart(mixed):
    by_gender = speech_time_by_gender(timeline_to_frame(mixed)).set_index("gender")
    assert by_gender["seconds"].to_dict() == {
        "mujer": 30, "hombre": 60, "desconocido": 10, "sin_atribuir": 20,
    }  # fmt: skip
    assert by_gender["share"]["mujer"] == pytest.approx(30 / 120)
    assert by_gender["share"].sum() == pytest.approx(1.0)


def test_time_by_speaker(mixed):
    df = speech_time_by_speaker(timeline_to_frame(mixed))
    assert dict(zip(df["speaker_id"], df["seconds"], strict=True)) == {
        "SPEAKER_00": 30, "SPEAKER_01": 60, "SPEAKER_02": 10,
    }  # fmt: skip


def test_sample_counts(mixed):
    s = sample_of(timeline_to_frame(mixed))
    assert (s.n_events, s.n_speakers, s.n_speakers_known_gender) == (4, 3, 2)
    assert s.known_gender_seconds == 90 and s.unattributed_share == pytest.approx(30 / 120)


def test_empty_timeline_does_not_crash():
    df = timeline_to_frame(timeline([], []))
    assert sample_of(df).speech_seconds == 0
    assert speech_time_by_gender(df)["share"].sum() == 0


def test_example_metric_is_registered_and_marked_as_example():
    spec = get_metric("X00_EJEMPLO")
    assert spec.is_example and "EJEMPLO" in spec.name
    ids = {m.metric_id for m in list_metrics()}
    assert ids == {"X00_EJEMPLO", "M01", "M02", "M03", "M04", "M13"}  # M01-M04 y M13 = borrador


def test_example_metric_value_and_sample_always_present(mixed):
    r = run_metric("X00_EJEMPLO", timeline_to_frame(mixed))
    assert r.conclusive and r.value == pytest.approx(33.33)  # 30 / (30 + 60)
    assert r.is_example and r.provenance == Provenance.COMPUTED
    assert r.sample["n_speakers_known_gender"] == 2 and r.sample["unattributed_share"] == 0.25


def test_insufficient_sample_is_not_conclusive_and_says_why():
    only_one = timeline([("SPEAKER_00", 100), ("SPEAKER_01", 100)], [woman(0), unknown(1)])
    r = run_metric("X00_EJEMPLO", timeline_to_frame(only_one))
    assert not r.conclusive and r.value is None
    assert "muestra insuficiente" in r.reason and "voces con género conocido 1 < 2" in r.reason


def test_too_little_known_time_is_not_conclusive():
    short = timeline([("SPEAKER_00", 3), ("SPEAKER_01", 3)], [woman(0), man(1)])
    r = run_metric("X00_EJEMPLO", timeline_to_frame(short))
    assert not r.conclusive and "segundos con género conocido 6 < 10" in r.reason


def test_all_unknown_is_not_conclusive():
    r = run_metric(
        "X00_EJEMPLO",
        timeline_to_frame(
            timeline([("SPEAKER_00", 99), ("SPEAKER_01", 99)], [unknown(0), unknown(1)])
        ),
    )
    assert not r.conclusive and r.sample["unattributed_share"] == 1.0


def test_unknown_metric_id():
    with pytest.raises(KeyError):
        run_metric("M99", timeline_to_frame(timeline([], [])))


def test_new_metric_follows_the_pattern_and_duplicates_are_rejected():
    @metric(metric_id="T_TMP", name="tmp", min_speakers_known_gender=1, min_known_gender_seconds=1)
    def tmp(frame):
        return MetricOutput(value=1.0, margin=0.1)

    with pytest.raises(ValueError):
        metric(
            metric_id="T_TMP", name="x", min_speakers_known_gender=1, min_known_gender_seconds=1
        )(tmp)
    from metrics.registry import _REGISTRY

    del _REGISTRY["T_TMP"]  # no contaminar el resto de tests


def test_metric_can_mark_itself_not_conclusive_with_a_reason():
    @metric(
        metric_id="T_REASON",
        name="tmp",
        min_speakers_known_gender=0,
        min_known_gender_seconds=0,
    )
    def tmp(frame):
        return MetricOutput(
            value=1.0, details={"clave": 2}, reason="no concluyente: pocas preguntas"
        )

    r = run_metric("T_REASON", timeline_to_frame(timeline([], [])))
    assert not r.conclusive and r.value is None
    assert r.reason == "no concluyente: pocas preguntas"
    assert r.details == {"clave": 2}
    from metrics.registry import _REGISTRY

    del _REGISTRY["T_REASON"]  # no contaminar el resto de tests


def test_gap_rule_requires_threshold_and_all_three_conditions():
    # sin umbral por defecto: es obligatorio
    with pytest.raises(TypeError):
        gap_is_conclusive(20.0, unattributed_share=0.0, margin=None)
    ok = dict(unattributed_share=5.0, margin=3.0)
    assert gap_is_conclusive(20.0, threshold=15, **ok) == (True, None)
    assert gap_is_conclusive(-20.0, threshold=15, **ok)[0] is True
    assert not gap_is_conclusive(10.0, threshold=15, **ok)[0]  # no supera el umbral
    assert not gap_is_conclusive(20.0, threshold=15, unattributed_share=25.0, margin=None)[0]
    assert not gap_is_conclusive(20.0, threshold=15, unattributed_share=0.0, margin=25.0)[0]
