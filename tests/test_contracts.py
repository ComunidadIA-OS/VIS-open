"""Tests de los contratos. Solo datos sintéticos: nunca audio ni transcripciones reales."""

import pytest
from pydantic import ValidationError

from contracts import (
    AnalysisEvent,
    AnalysisTimeline,
    EventType,
    GenderSource,
    GenderValue,
    GestureRow,
    Provenance,
    ReviewRow,
    Speaker,
    read_rows,
    write_rows,
)


def event(**kw):
    base = dict(
        event_id="e1",
        type=EventType.SPEECH,
        start_s=1.0,
        end_s=2.0,
        speaker_id="SPEAKER_00",
        provenance=Provenance.OBSERVED,
    )
    base.update(kw)
    return AnalysisEvent(**base)


def test_valid_event():
    assert event().end_s == 2.0


def test_end_before_start_fails():
    with pytest.raises(ValidationError):
        event(start_s=5.0, end_s=1.0)


@pytest.mark.parametrize("conf", [-0.1, 1.1])
def test_confidence_out_of_range_fails(conf):
    with pytest.raises(ValidationError):
        event(confidence=conf)


def test_bad_speaker_id_fails():
    with pytest.raises(ValidationError):
        event(speaker_id="Ana")


def test_extra_fields_rejected():
    with pytest.raises(ValidationError):
        event(inventado=1)


@pytest.mark.parametrize(
    ("provenance", "confidence", "expected"),
    [
        (Provenance.AI_INFERRED, 0.69, True),
        (Provenance.AI_INFERRED, 0.7, False),
        (Provenance.AI_INFERRED, None, True),
        (Provenance.OBSERVED, 0.1, False),
        (Provenance.HUMAN_VALIDATED, None, False),
    ],
)
def test_needs_review(provenance, confidence, expected):
    assert event(provenance=provenance, confidence=confidence).needs_review is expected


def test_hand_raise_fields_only_for_hand_raise():
    with pytest.raises(ValidationError):
        event(zone_id="z1")
    ok = event(type=EventType.HAND_RAISE, speaker_id=None, zone_id="z1", granted=True)
    assert ok.granted is True


def test_speaker_gender_and_source_must_match():
    Speaker(speaker_id="SPEAKER_01")
    Speaker(
        speaker_id="SPEAKER_01",
        gender=GenderValue.WOMAN,
        gender_source=GenderSource.PERCEIVED_BY_ANNOTATORS,
    )
    with pytest.raises(ValidationError):
        Speaker(speaker_id="SPEAKER_01", gender=GenderValue.WOMAN)
    with pytest.raises(ValidationError):
        Speaker(speaker_id="SPEAKER_01", gender_source=GenderSource.DECLARED)


def test_unknown_is_the_default_gender():
    s = Speaker(speaker_id="SPEAKER_02")
    assert s.gender == GenderValue.UNKNOWN
    assert s.gender_source == GenderSource.UNKNOWN


def timeline(**kw):
    base = dict(
        video_id="demo-01",
        duration_s=60,
        speakers=[Speaker(speaker_id="SPEAKER_00")],
        events=[event()],
    )
    base.update(kw)
    return AnalysisTimeline(**base)


def test_timeline_valid_and_roundtrip():
    t = timeline()
    assert AnalysisTimeline.model_validate_json(t.model_dump_json()) == t


def test_timeline_unknown_speaker_fails():
    with pytest.raises(ValidationError):
        timeline(events=[event(speaker_id="SPEAKER_09")])


def test_timeline_duplicate_event_id_fails():
    with pytest.raises(ValidationError):
        timeline(events=[event(), event()])


def test_timeline_event_after_duration_fails():
    with pytest.raises(ValidationError):
        timeline(events=[event(end_s=61)])


def test_gesture_needs_speaker_or_zone():
    GestureRow(video_id="v", start_s=3.0, zone_id="z1")
    with pytest.raises(ValidationError):
        GestureRow(video_id="v", start_s=3.0)


def test_review_csv_roundtrip(tmp_path):
    rows = [
        ReviewRow(
            video_id="demo-01",
            speaker_id="SPEAKER_00",
            total_seconds=120.5,
            fragment_1_start_s=10,
            fragment_2_start_s=50,
            fragment_3_start_s=90,
        ),
        ReviewRow(
            video_id="demo-01",
            speaker_id="SPEAKER_01",
            total_seconds=30,
            annotator_id="A1",
            gender=GenderValue.UNKNOWN,
            role="moderación",
            notes="voz poco clara",
        ),
    ]
    path = tmp_path / "review.csv"
    write_rows(rows, ReviewRow, path)
    assert read_rows(ReviewRow, path) == rows


def test_review_csv_rejects_invented_gender(tmp_path):
    path = tmp_path / "bad.csv"
    header = ",".join(ReviewRow.model_fields)
    values = {
        "video_id": "v",
        "speaker_id": "SPEAKER_00",
        "total_seconds": "1",
        "gender": "otro",
    }
    line = ",".join(values.get(c, "") for c in ReviewRow.model_fields)
    path.write_text(f"{header}\n{line}\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        read_rows(ReviewRow, path)


def test_review_csv_missing_columns(tmp_path):
    path = tmp_path / "short.csv"
    path.write_text("video_id,speaker_id\nv,SPEAKER_00\n", encoding="utf-8")
    with pytest.raises(ValueError, match="faltan columnas"):
        read_rows(ReviewRow, path)


def test_gesture_csv_roundtrip(tmp_path):
    rows = [GestureRow(video_id="v", start_s=12.0, zone_id="z2", granted=False)]
    path = tmp_path / "gestures.csv"
    write_rows(rows, GestureRow, path)
    assert read_rows(GestureRow, path) == rows
