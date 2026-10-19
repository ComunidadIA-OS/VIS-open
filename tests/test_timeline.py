import json

import pytest

from contracts import AnalysisTimeline, GenderValue, Provenance, ReviewRow, read_rows
from pipeline.diarize import SpeakerTurn
from pipeline.timeline import assign_speaker, build_review_rows, build_timeline, write_outputs
from pipeline.transcribe import Segment

SRC = "faster-whisper:small"
TURNS = [
    SpeakerTurn(0.0, 4.0, "SPEAKER_00"),
    SpeakerTurn(4.0, 6.0, "SPEAKER_01"),
    SpeakerTurn(6.0, 9.0, "SPEAKER_00"),
]
SEGMENTS = [
    Segment(6.5, 8.5, "tercera", 0.4, SRC),
    Segment(0.0, 3.5, "primera", 0.9, SRC),
    Segment(3.5, 5.5, "solapa más con la 01", 0.8, SRC),
    Segment(9.5, 10.5, "nadie habla aquí según la diarización", None, SRC),
]


@pytest.fixture
def timeline() -> AnalysisTimeline:
    return build_timeline("debate_sintetico", 10.0, SEGMENTS, TURNS)


def test_assign_speaker_max_overlap_or_none():
    assert assign_speaker(SEGMENTS[2], TURNS) == "SPEAKER_01"
    assert assign_speaker(SEGMENTS[3], TURNS) is None
    assert assign_speaker(SEGMENTS[0], []) is None


def test_build_timeline(timeline):
    assert [s.speaker_id for s in timeline.speakers] == ["SPEAKER_00", "SPEAKER_01"]
    assert [s.total_speech_s for s in timeline.speakers] == [7.0, 2.0]
    # Nunca se deduce el género: siempre desconocido hasta la anotación humana.
    assert all(s.gender == GenderValue.UNKNOWN for s in timeline.speakers)

    texts = [e.text for e in timeline.events]
    assert texts[0] == "primera" and texts[-1].startswith("nadie")
    assert [e.event_id for e in timeline.events] == ["ev_00000", "ev_00001", "ev_00002", "ev_00003"]
    assert all(e.provenance == Provenance.AI_INFERRED for e in timeline.events)

    unattributed = timeline.events[-1]
    assert unattributed.speaker_id is None and unattributed.source == SRC
    assert timeline.events[0].source == SRC + "+pyannote"
    assert unattributed.needs_review  # sin confianza → revisión humana
    assert timeline.events[2].needs_review  # 0.4 < 0.7


def test_build_timeline_clamps_to_duration():
    tl = build_timeline(
        "v", 5.0, [Segment(4.0, 5.3, "x", 0.9, SRC)], [SpeakerTurn(4.0, 5.3, "SPEAKER_00")]
    )
    assert tl.events[0].end_s == 5.0
    assert tl.speakers[0].total_speech_s == 1.0


def test_review_rows_fragments(timeline):
    rows = build_review_rows(timeline, "anotadora_1")
    by_id = {r.speaker_id: r for r in rows}
    sp0, sp1 = by_id["SPEAKER_00"], by_id["SPEAKER_01"]
    assert (sp0.fragment_1_start_s, sp0.fragment_2_start_s, sp0.fragment_3_start_s) == (
        0.0,
        6.5,
        None,
    )
    assert (sp1.fragment_1_start_s, sp1.fragment_2_start_s) == (3.5, None)
    assert sp0.total_seconds == 7.0 and sp0.annotator_id == "anotadora_1"
    assert sp0.gender is None and sp0.confidence is None  # lo rellena la persona


def test_review_rows_pick_three_longest():
    segs = [
        Segment(float(i), i + d, f"s{i}", 0.9, SRC)
        for i, d in [(0, 0.2), (1, 0.9), (2, 0.5), (3, 0.8)]
    ]
    tl = build_timeline("v", 10.0, segs, [SpeakerTurn(0.0, 4.0, "SPEAKER_00")])
    row = build_review_rows(tl, "a")[0]
    assert (row.fragment_1_start_s, row.fragment_2_start_s, row.fragment_3_start_s) == (
        1.0,
        2.0,
        3.0,
    )


def test_write_outputs_roundtrip(timeline, tmp_path):
    paths = write_outputs(timeline, tmp_path / "out")
    assert [p.name for p in paths] == [
        "timeline.json",
        "review_anotadora_1.csv",
        "review_anotadora_2.csv",
    ]
    loaded = AnalysisTimeline.model_validate(json.loads(paths[0].read_text(encoding="utf-8")))
    assert loaded == timeline
    for path, annotator in zip(paths[1:], ["anotadora_1", "anotadora_2"], strict=True):
        rows = read_rows(ReviewRow, path)
        assert {r.annotator_id for r in rows} == {annotator}
        assert len(rows) == 2
