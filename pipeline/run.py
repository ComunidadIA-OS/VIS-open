"""Ejecuta el pipeline completo sobre un vídeo.

Uso: python -m pipeline.run data/raw/debate.mp4
Salida en $DATA_DIR/processed/<nombre_del_vídeo>/ (DATA_DIR por defecto ./data, ignorado por git).
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from pipeline.audio import extract_audio, wav_duration_s
from pipeline.diarize import DiarizeConfig, diarize
from pipeline.timeline import build_timeline, write_outputs
from pipeline.transcribe import TranscribeConfig, transcribe


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    args = parser.parse_args(argv)

    out_dir = Path(os.environ.get("DATA_DIR") or "data") / "processed" / args.video.stem
    wav = extract_audio(args.video, out_dir / "audio.wav")
    segments = transcribe(wav, TranscribeConfig.from_env())
    turns = diarize(wav, DiarizeConfig.from_env())
    timeline = build_timeline(args.video.stem, wav_duration_s(wav), segments, turns)
    for path in write_outputs(timeline, out_dir):
        print(path)


if __name__ == "__main__":
    main()
