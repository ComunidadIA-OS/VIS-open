"""Extracción de audio con FFmpeg (binario externo, LGPL-2.1+)."""

from __future__ import annotations

import shutil
import subprocess
import wave
from pathlib import Path

SAMPLE_RATE = 16_000


def ffmpeg_command(
    video: Path,
    wav: Path,
    ffmpeg: str = "ffmpeg",
    start_s: float = 0.0,
    end_s: float | None = None,
) -> list[str]:
    """Comando para pasar un vídeo (o su tramo [start_s, end_s]) a WAV 16 bits, 16 kHz, mono."""
    tramo = ["-ss", f"{start_s:.3f}"] if start_s else []
    if end_s is not None:
        tramo += ["-t", f"{end_s - start_s:.3f}"]
    return [
        ffmpeg,
        "-nostdin",
        "-y",
        "-loglevel",
        "error",
        *tramo,
        "-i",
        str(video),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(SAMPLE_RATE),
        "-c:a",
        "pcm_s16le",
        str(wav),
    ]


def extract_audio(video: Path, wav: Path, start_s: float = 0.0, end_s: float | None = None) -> Path:
    """Extrae el audio de `video` (o de un tramo) a `wav`. Lanza RuntimeError si FFmpeg falla."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("FFmpeg no está instalado o no está en el PATH")
    video, wav = Path(video), Path(wav)
    if not video.is_file():
        raise FileNotFoundError(video)
    wav.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ffmpeg_command(video, wav, ffmpeg, start_s, end_s), capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg falló: {result.stderr.strip()}")
    return wav


def wav_duration_s(wav: Path) -> float:
    with wave.open(str(wav), "rb") as fh:
        return fh.getnframes() / fh.getframerate()
