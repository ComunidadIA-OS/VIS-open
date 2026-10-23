import csv

from pipeline import sesion
from sources.manifest import COLUMNS


def _data(tmp_path, ids):
    with (tmp_path / "manifiesto.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, COLUMNS)
        w.writeheader()
        for vid in ids:
            w.writerow({"video_id": vid})
    (tmp_path / "raw").mkdir()
    return tmp_path


def test_pending_are_sessions_with_video_and_no_timeline(tmp_path):
    data = _data(tmp_path, ["V005", "V008", "V009"])
    for vid in ("V005", "V008"):
        (data / "raw" / f"{vid}.mp4").write_bytes(b"x")
    (data / "processed" / "V005").mkdir(parents=True)
    (data / "processed" / "V005" / "timeline.json").write_text("{}")
    assert sesion.pending(data) == ["V008"]  # V005 ya hecha; V009 sin vídeo


def test_steps_in_order_and_engine_from_environment(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(sesion, "require_ready", lambda *a: {})
    monkeypatch.setattr(
        sesion, "_run", lambda *a: calls.append(a[0] if a[0] != "metrics.m09" else a)
    )
    monkeypatch.setenv("LLM_API_KEY", "x")
    monkeypatch.delenv("POSE_MODEL", raising=False)
    sesion.analyze_session("V008", tmp_path)
    assert calls[:2] == ["pipeline.run", "decision.roles"]
    assert calls[2][-2:] == ("--engine", "llm") and len(calls) == 3  # sin POSE_MODEL, sin vídeo


def test_new_videos_are_the_ones_without_a_manifest_row(tmp_path):
    data = _data(tmp_path, ["V005"])
    for vid in ("V005", "V008"):
        (data / "raw" / f"{vid}.mp4").write_bytes(b"x")
    assert [v.stem for v in sesion.new_videos(data)] == ["V008"]
