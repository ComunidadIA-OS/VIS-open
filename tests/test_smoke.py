import json
import wave

from pipeline.diarize import SpeakerTurn
from pipeline.smoke import make_tone_wav, run_smoke
from pipeline.transcribe import Segment


def test_tone_wav_is_valid(tmp_path):
    wav = make_tone_wav(tmp_path / "t.wav", seconds=2)
    with wave.open(str(wav), "rb") as fh:
        assert fh.getframerate() == 16_000 and fh.getnframes() == 32_000


def test_run_smoke_reports_steps_without_text(tmp_path):
    wav = make_tone_wav(tmp_path / "t.wav", seconds=1)
    segs = [Segment(0.0, 1.0, "texto secreto", 0.9, "fake")]
    turns = [SpeakerTurn(0.0, 1.0, "SPEAKER_00"), SpeakerTurn(1.0, 2.0, "SPEAKER_01")]
    report = run_smoke(wav, lambda p: segs, lambda p: turns)
    assert report["steps"]["transcribe"]["segments"] == 1
    assert report["steps"]["diarize"]["voices"] == 2
    assert "texto secreto" not in json.dumps(report)


def test_run_smoke_skips_diarization_without_token(tmp_path):
    wav = make_tone_wav(tmp_path / "t.wav", seconds=1)
    report = run_smoke(wav, lambda p: [], None)
    assert report["steps"]["diarize"]["status"] == "omitido"
