"""Transcripción con faster-whisper y alineado de tiempos con WhisperX.

Configuración por variables de entorno (ver `.env.example`):
- WHISPER_DEVICE: `cpu` (por defecto) o `cuda`.
- WHISPER_MODEL: por defecto `small` en CPU y `large-v3` en GPU.
- WHISPER_COMPUTE_TYPE: por defecto `int8` en CPU y `float16` en GPU.
  Las V100S (Volta) no tienen bf16, así que se rechaza cualquier tipo bfloat16.
- WHISPER_LANGUAGE: por defecto `es`; vacío = detección automática.
- WHISPER_ALIGN: `1` (por defecto) alinea con WhisperX; `0` lo desactiva.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULTS = {
    "cpu": {"model": "small", "compute_type": "int8"},
    "cuda": {"model": "large-v3", "compute_type": "float16"},
}


@dataclass(frozen=True)
class TranscribeConfig:
    device: str = "cpu"
    model: str = "small"
    compute_type: str = "int8"
    language: str | None = "es"
    align: bool = True

    def __post_init__(self) -> None:
        if self.device not in DEFAULTS:
            raise ValueError(f"WHISPER_DEVICE debe ser 'cpu' o 'cuda', no {self.device!r}")
        if "bfloat16" in self.compute_type:
            raise ValueError("bfloat16 no está soportado en las V100S: usa float16 o int8")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> TranscribeConfig:
        env = os.environ if env is None else env
        device = env.get("WHISPER_DEVICE") or "cpu"
        defaults = DEFAULTS.get(device, DEFAULTS["cpu"])
        language = env.get("WHISPER_LANGUAGE", "es")
        return cls(
            device=device,
            model=env.get("WHISPER_MODEL") or defaults["model"],
            compute_type=env.get("WHISPER_COMPUTE_TYPE") or defaults["compute_type"],
            language=language or None,
            align=env.get("WHISPER_ALIGN", "1") != "0",
        )


@dataclass(frozen=True)
class Segment:
    start_s: float
    end_s: float
    text: str
    confidence: float | None
    source: str


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def transcribe(wav: Path, config: TranscribeConfig) -> list[Segment]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "falta faster-whisper: instala el extra con pip install -e '.[pipeline]'"
        ) from exc

    model = WhisperModel(config.model, device=config.device, compute_type=config.compute_type)
    raw, info = model.transcribe(
        str(wav), language=config.language, word_timestamps=True, vad_filter=True
    )
    segments = [
        Segment(
            start_s=s.start,
            end_s=s.end,
            text=s.text.strip(),
            confidence=_mean([w.probability for w in s.words or []]),
            source=f"faster-whisper:{config.model}",
        )
        for s in raw
    ]
    if config.align and segments:
        segments = align(wav, segments, info.language, config.device)
    return segments


def align(wav: Path, segments: list[Segment], language: str, device: str) -> list[Segment]:
    try:
        import whisperx
    except ImportError as exc:
        raise RuntimeError(
            "falta WhisperX (requiere Python < 3.14): instala el extra '.[align]' "
            "o desactiva el alineado con WHISPER_ALIGN=0"
        ) from exc

    model, metadata = whisperx.load_align_model(language_code=language, device=device)
    audio = whisperx.load_audio(str(wav))
    result = whisperx.align(
        [{"start": s.start_s, "end": s.end_s, "text": s.text} for s in segments],
        model,
        metadata,
        audio,
        device,
        return_char_alignments=False,
    )
    source = f"{segments[0].source}+whisperx"
    return [
        Segment(
            start_s=seg["start"],
            end_s=seg["end"],
            text=seg["text"].strip(),
            confidence=_mean([w["score"] for w in seg.get("words", []) if "score" in w]),
            source=source,
        )
        for seg in result["segments"]
        if seg.get("start") is not None and seg.get("end") is not None
    ]
