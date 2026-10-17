"""Prueba de humo: pasa un audio corto por transcripción y diarización y mide tiempo y memoria.

Uso: python -m pipeline.smoke [audio.wav] [--out data/smoke.json]
Sin audio, genera un tono sintético (no hay voz, solo sirve para comprobar que todo arranca).
Si falta HF_TOKEN, la diarización se registra como omitida en vez de fallar.
No guarda texto ni audio: solo tiempos, memoria y versiones.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import struct
import time
import wave
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pipeline.diarize import DiarizeConfig, diarize
from pipeline.transcribe import TranscribeConfig, transcribe


def make_tone_wav(path: Path, seconds: int = 5, rate: int = 16_000) -> Path:
    """WAV sintético mono de 16 bits: un tono de 440 Hz."""
    frames = b"".join(
        struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / rate)))
        for i in range(rate * seconds)
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(rate)
        fh.writeframes(frames)
    return path


def _peak_rss_mb() -> float | None:
    """Memoria máxima del proceso en MB (solo Linux/macOS; en Windows, None)."""
    try:
        import resource
    except ImportError:
        return None
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(peak / (1024 if platform.system() == "Linux" else 1024 * 1024), 1)


def _torch_info() -> dict[str, Any]:
    try:
        import torch
    except ImportError:
        return {"torch": None}
    info: dict[str, Any] = {"torch": torch.__version__, "cuda_available": torch.cuda.is_available()}
    if torch.cuda.is_available():
        info["gpu"] = torch.cuda.get_device_name(0)
        info["gpu_compute_capability"] = ".".join(map(str, torch.cuda.get_device_capability(0)))
        info["gpu_arch_list"] = torch.cuda.get_arch_list()
        # Volta (V100S) es sm_70: si el wheel no lo trae, la GPU no se puede usar.
        info["volta_sm70_supported"] = "sm_70" in torch.cuda.get_arch_list()
        info["gpu_peak_mem_mb"] = round(torch.cuda.max_memory_allocated() / 2**20, 1)
    return info


def _timed(fn: Callable[[], Any]) -> tuple[Any, float]:
    start = time.perf_counter()
    result = fn()
    return result, round(time.perf_counter() - start, 3)


def run_smoke(
    wav: Path,
    transcribe_fn: Callable[[Path], list],
    diarize_fn: Callable[[Path], list] | None,
) -> dict[str, Any]:
    """Ejecuta los pasos y devuelve el informe (sin texto transcrito)."""
    with wave.open(str(wav), "rb") as fh:
        audio_s = round(fh.getnframes() / fh.getframerate(), 3)
    report: dict[str, Any] = {"audio_s": audio_s, "steps": {}}

    segments, secs = _timed(lambda: transcribe_fn(wav))
    report["steps"]["transcribe"] = {"status": "ok", "seconds": secs, "segments": len(segments)}

    if diarize_fn is None:
        report["steps"]["diarize"] = {"status": "omitido", "reason": "falta HF_TOKEN"}
    else:
        turns, secs = _timed(lambda: diarize_fn(wav))
        report["steps"]["diarize"] = {
            "status": "ok",
            "seconds": secs,
            "voices": len({t.speaker_id for t in turns}),
        }
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path, nargs="?")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    data_dir = Path(os.environ.get("DATA_DIR") or "data")
    wav = args.audio or make_tone_wav(data_dir / "smoke" / "tone.wav")
    out = args.out or data_dir / "smoke.json"

    t_config = TranscribeConfig.from_env()
    try:
        d_config: DiarizeConfig | None = DiarizeConfig.from_env()
    except RuntimeError:
        d_config = None

    report = run_smoke(
        wav,
        lambda p: transcribe(p, t_config),
        (lambda p: diarize(p, d_config)) if d_config else None,
    )
    report["config"] = {
        "device": t_config.device,
        "model": t_config.model,
        "compute_type": t_config.compute_type,
        "python": platform.python_version(),
    }
    report["peak_rss_mb"] = _peak_rss_mb()
    report.update(_torch_info())

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
