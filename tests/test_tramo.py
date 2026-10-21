"""Tramo del manifiesto: solo se analiza el bloque indicado, con los tiempos del vídeo original."""

import shutil
import subprocess

import pytest

from pipeline.audio import ffmpeg_command
from pipeline.diarize import SpeakerTurn
from pipeline.timeline import build_timeline, shift_times
from pipeline.transcribe import Segment
from sources.manifest import ManifestError, parse_hms, tramo_s


def test_parse_hms_and_tramo_from_a_manifest_row():
    assert parse_hms("01:02:03") == 3723 and parse_hms("00:00:07.5") == 7.5
    assert tramo_s({"tramo_inicio": "00:10:00", "tramo_fin": "01:30:00"}) == (600.0, 5400.0)
    assert tramo_s({"tramo_inicio": "", "tramo_fin": ""}) == (0.0, None)  # sin tramo: todo
    assert tramo_s({"tramo_inicio": "00:05:00"}) == (300.0, None)
    with pytest.raises(ManifestError):
        tramo_s({"tramo_inicio": "01:00:00", "tramo_fin": "00:30:00"})


def test_ffmpeg_only_takes_the_requested_stretch():
    full = ffmpeg_command("v.mp4", "a.wav")
    assert "-ss" not in full and "-t" not in full
    cut = ffmpeg_command("v.mp4", "a.wav", start_s=600.0, end_s=900.0)
    assert cut[cut.index("-ss") + 1] == "600.000" and cut[cut.index("-t") + 1] == "300.000"
    assert cut.index("-ss") < cut.index("-i")  # antes de -i: salto rápido


def test_shifted_timeline_uses_original_video_times():
    segs = [Segment(1.0, 4.0, "hola", 0.9, "t")]
    turns = [SpeakerTurn(0.5, 5.0, "SPEAKER_00")]
    segs2, turns2 = shift_times(segs, turns, 600.0)
    tl = build_timeline("V", 610.0, segs2, turns2)
    assert (tl.events[0].start_s, tl.events[0].end_s) == (601.0, 604.0)
    assert tl.duration_s == 610.0 and tl.speakers[0].total_speech_s == 4.5
    same = shift_times(segs, turns, 0.0)
    assert same == (segs, turns)  # sin tramo no cambia nada


def test_video_frames_only_come_from_the_tramo(tmp_path):
    cv2 = pytest.importorskip("cv2")
    if shutil.which("ffmpeg") is None:
        pytest.skip("hace falta FFmpeg")
    from pipeline.video import iter_video_frames

    src = tmp_path / "t.mp4"
    subprocess.run(  # vídeo de prueba de 10 s generado por FFmpeg, no es un vídeo real
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=64x48:rate=10",
         "-t", "10", "-pix_fmt", "yuv420p", str(src)],
        check=True,
    )  # fmt: skip
    times = [t for t, _ in iter_video_frames(src, sample_fps=1.0, start_s=4.0, end_s=7.0)]
    assert cv2 is not None and times and min(times) >= 4.0 and max(times) <= 7.0
    assert len(times) in (3, 4)
