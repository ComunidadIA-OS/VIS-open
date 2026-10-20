"""Personas visibles y manos levantadas con poses SINTÉTICAS (sin imagen ni MediaPipe)."""

import pytest

from pipeline.gestures import Point
from pipeline.video import analyze_frames, iter_video_frames, summarize, zone_of


def person(x, wrist_y=0.8):
    """Pose sintética: hombros en y=0.4 alrededor de x; muñecas en wrist_y."""
    return {
        11: Point(x + 0.02, 0.4), 12: Point(x - 0.02, 0.4),
        15: Point(x + 0.03, wrist_y), 16: Point(x - 0.03, wrist_y),
    }  # fmt: skip


def run(timeline_of_poses, fps=2.0):
    frames = [(i / fps, poses) for i, poses in enumerate(timeline_of_poses)]
    return analyze_frames(frames, lambda poses: poses)  # el «detector» devuelve las poses dadas


def test_zone_of_by_shoulder_midpoint():
    assert [zone_of(person(x)) for x in (0.05, 0.3, 0.6, 0.95)] == ["Z1", "Z2", "Z3", "Z4"]


def test_counts_people_and_ignores_arms_down():
    res = run([[person(0.2), person(0.6)], [person(0.2)], []])
    s = summarize(res)
    assert [r.n_people for r in res] == [2, 1, 0]
    assert s["personas_visibles_max"] == 2 and s["personas_visibles_mediana"] == 1.0
    assert s["fotogramas_sin_personas_%"] == pytest.approx(33.3)
    assert s["manos_levantadas"] == []


def test_sustained_raise_is_assigned_to_a_zone_not_a_person():
    up = person(0.3, wrist_y=0.1)  # zona Z2
    seq = [[person(0.3)]] + [[up, person(0.8)]] * 4 + [[person(0.3)]]
    s = summarize(run(seq))
    assert s["manos_levantadas_por_zona"] == {"Z2": 2}  # ambas muñecas de esa persona
    assert {h["zona"] for h in s["manos_levantadas"]} == {"Z2"}
    assert "identific" in s["aviso"]


def test_short_raise_is_discarded():
    seq = [[person(0.3)], [person(0.3, 0.1)], [person(0.3)], [person(0.3)]]
    assert summarize(run(seq))["manos_levantadas"] == []


def test_empty_video():
    assert summarize([]) == {"n_fotogramas": 0}


def test_iter_video_frames_samples_and_reads_real_file(tmp_path):
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    path = tmp_path / "t.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (64, 48))
    if not writer.isOpened():
        pytest.skip("este OpenCV no puede escribir mp4")
    for _ in range(30):  # 3 s a 10 fps
        writer.write(np.zeros((48, 64, 3), dtype="uint8"))
    writer.release()
    frames = list(iter_video_frames(path, sample_fps=2))
    assert len(frames) == 6 and frames[1][0] == pytest.approx(0.5, abs=0.01)
    assert frames[0][1].shape == (48, 64, 3)
