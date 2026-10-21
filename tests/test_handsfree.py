import base64
import shutil
import subprocess
from pathlib import Path

import pytest

from dashboard import voice
from dashboard.handsfree import decode_audio

WAV = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 40


def test_decode_audio_accepts_a_wav_only():
    b64 = base64.b64encode(WAV).decode()
    assert decode_audio({"b64": b64, "id": 1}) == WAV
    for bad in (None, {}, {"b64": 3}, {"b64": ""}, {"b64": "!!no-base64!!"}):
        with pytest.raises(ValueError):
            decode_audio(bad)
    with pytest.raises(ValueError):  # base64 válido pero no es un WAV
        decode_audio({"b64": base64.b64encode(b"MZ" + b"\x00" * 20).decode()})
    with pytest.raises(ValueError):  # demasiado grande
        decode_audio({"b64": "A" * 6_000_004})


def test_handsfree_off_commands():
    for text in ("desactiva el modo manos libres", "deja de escuchar", "hasta luego"):
        assert voice.parse_command(text, ["V001"]).action == "handsfree_off"


@pytest.mark.skipif(shutil.which("node") is None, reason="Node no está instalado")
@pytest.mark.skipif(
    not (Path(__file__).parent / "fixtures" / "voz").is_dir(), reason="faltan las frases de prueba"
)
def test_voice_activity_detector_with_synthetic_audio():
    root = Path(__file__).parent
    run = subprocess.run(
        ["node", str(root / "vad.test.mjs")], capture_output=True, text=True, timeout=60
    )
    assert run.returncode == 0, run.stderr
    assert "vad: ok" in run.stdout
