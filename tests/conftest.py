import math
import struct
import wave
from pathlib import Path

import pytest


@pytest.fixture
def sine_wav(tmp_path: Path) -> Path:
    """WAV sintético de 2 s, 16 kHz mono: un tono de 440 Hz (sin voz real)."""
    path = tmp_path / "tone.wav"
    rate, seconds = 16_000, 2
    frames = b"".join(
        struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / rate)))
        for i in range(rate * seconds)
    )
    with wave.open(str(path), "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(rate)
        fh.writeframes(frames)
    return path
