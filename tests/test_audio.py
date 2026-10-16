import shutil
import subprocess
from pathlib import Path

import pytest

from pipeline import audio
from pipeline.audio import SAMPLE_RATE, extract_audio, ffmpeg_command, wav_duration_s

HAS_FFMPEG = shutil.which("ffmpeg") is not None


def test_ffmpeg_command_is_16k_mono_pcm():
    cmd = ffmpeg_command(Path("in.mp4"), Path("out.wav"))
    assert cmd[cmd.index("-ac") + 1] == "1"
    assert cmd[cmd.index("-ar") + 1] == str(SAMPLE_RATE) == "16000"
    assert cmd[cmd.index("-c:a") + 1] == "pcm_s16le"
    assert "-vn" in cmd and "-nostdin" in cmd
    assert cmd[-1] == "out.wav"


def test_extract_audio_without_ffmpeg(monkeypatch, tmp_path):
    monkeypatch.setattr(audio.shutil, "which", lambda _: None)
    with pytest.raises(RuntimeError, match="FFmpeg no está instalado"):
        extract_audio(tmp_path / "x.mp4", tmp_path / "x.wav")


def test_extract_audio_missing_video(monkeypatch, tmp_path):
    monkeypatch.setattr(audio.shutil, "which", lambda _: "ffmpeg")
    with pytest.raises(FileNotFoundError):
        extract_audio(tmp_path / "no_existe.mp4", tmp_path / "x.wav")


def test_wav_duration(sine_wav):
    assert wav_duration_s(sine_wav) == pytest.approx(2.0)


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg no está en el PATH")
def test_extract_audio_from_synthetic_video(tmp_path):
    video = tmp_path / "synthetic.mkv"
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=1:size=64x64:rate=5",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1:sample_rate=44100",
            "-ac",
            "2",
            "-shortest",
            str(video),
        ],
        check=True,
    )
    wav = extract_audio(video, tmp_path / "out" / "audio.wav")
    import wave

    with wave.open(str(wav), "rb") as fh:
        assert fh.getnchannels() == 1
        assert fh.getframerate() == SAMPLE_RATE
    assert wav_duration_s(wav) == pytest.approx(1.0, abs=0.1)
