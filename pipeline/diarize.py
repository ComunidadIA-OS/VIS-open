"""Diarización (quién habla y cuándo) con pyannote.audio.

Solo separa voces anónimas (SPEAKER_00, SPEAKER_01...). No identifica a nadie ni
deduce el género: eso lo anotan dos personas en la tabla de revisión.

Configuración por variables de entorno (ver `.env.example`):
- HF_TOKEN: token de Hugging Face (el modelo es de acceso restringido). Nunca en el repo.
- DIARIZATION_MODEL: por defecto `pyannote/speaker-diarization-3.1`.
- WHISPER_DEVICE: se reutiliza para elegir `cpu` o `cuda`.
"""

from __future__ import annotations

import os
import wave
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL = "pyannote/speaker-diarization-3.1"


@dataclass(frozen=True)
class SpeakerTurn:
    start_s: float
    end_s: float
    speaker_id: str


@dataclass(frozen=True)
class DiarizeConfig:
    token: str
    model: str = DEFAULT_MODEL
    device: str = "cpu"

    def __repr__(self) -> str:  # que el token no acabe en logs
        return f"DiarizeConfig(model={self.model!r}, device={self.device!r}, token='***')"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> DiarizeConfig:
        env = os.environ if env is None else env
        token = env.get("HF_TOKEN", "").strip()
        if not token:
            raise RuntimeError("falta HF_TOKEN en el entorno (.env): pyannote lo necesita")
        return cls(
            token=token,
            model=env.get("DIARIZATION_MODEL") or DEFAULT_MODEL,
            device=env.get("WHISPER_DEVICE") or "cpu",
        )


def normalize_labels(raw: list[tuple[float, float, str]]) -> list[SpeakerTurn]:
    """Renombra las etiquetas de pyannote a SPEAKER_00, SPEAKER_01... por orden de aparición."""
    mapping: dict[str, str] = {}
    turns = []
    for start, end, label in sorted(raw, key=lambda t: (t[0], t[1])):
        if label not in mapping:
            mapping[label] = f"SPEAKER_{len(mapping):02d}"
        turns.append(SpeakerTurn(start_s=start, end_s=end, speaker_id=mapping[label]))
    if len(mapping) > 100:
        raise ValueError("más de 100 voces: el formato SPEAKER_NN no lo admite")
    return turns


def load_waveform(wav: Path) -> dict:
    """Lee un WAV PCM de 16 bits como forma de onda para pyannote.

    Evita torchcodec, que en Windows exige las DLL de FFmpeg «shared». El audio de
    `pipeline.audio` ya sale en PCM 16 bits, 16 kHz, mono.
    """
    import torch

    with wave.open(str(wav), "rb") as fh:
        if fh.getsampwidth() != 2:
            raise ValueError("se espera un WAV PCM de 16 bits (el que genera extract_audio)")
        channels, rate = fh.getnchannels(), fh.getframerate()
        raw = fh.readframes(fh.getnframes())
    data = torch.frombuffer(bytearray(raw), dtype=torch.int16).float() / 32768.0
    return {"waveform": data.reshape(-1, channels).T.contiguous(), "sample_rate": rate}


def diarize(wav: Path, config: DiarizeConfig) -> list[SpeakerTurn]:
    # Telemetría de pyannote desactivada: todo se queda en local.
    os.environ["PYANNOTE_METRICS_ENABLED"] = "0"
    try:
        import torch
        from pyannote.audio import Pipeline
    except ImportError as exc:
        raise RuntimeError(
            "falta pyannote.audio: instala el extra con pip install -e '.[pipeline]'"
        ) from exc

    pipeline = Pipeline.from_pretrained(config.model, token=config.token)
    pipeline.to(torch.device(config.device))
    output = pipeline(load_waveform(wav))
    # pyannote 4 devuelve un objeto con .speaker_diarization; 3.x, la anotación directamente.
    annotation = getattr(output, "speaker_diarization", output)
    return normalize_labels(
        [
            (turn.start, turn.end, label)
            for turn, _, label in annotation.itertracks(yield_label=True)
        ]
    )
