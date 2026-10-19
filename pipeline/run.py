"""Ejecuta el pipeline completo sobre un vídeo.

Uso: python -m pipeline.run data/raw/debate.mp4
Salida en $DATA_DIR/processed/<nombre_del_vídeo>/ (DATA_DIR por defecto ./data, ignorado por git).
El nombre del vídeo (sin extensión) es su `video_id` en el manifiesto ($DATA_DIR/manifiesto.csv o
--manifest): si su fila no está completa, no se analiza. Junto a la salida se escribe `source.json`
con la fuente y la fecha para citarlas.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from pipeline.audio import extract_audio, wav_duration_s
from pipeline.diarize import DiarizeConfig, diarize
from pipeline.timeline import build_timeline, write_outputs
from pipeline.transcribe import TranscribeConfig, transcribe
from sources.manifest import ManifestError, require_ready

CITED_FIELDS = (
    "video_id", "titulo", "fuente", "url_origen", "fecha_evento", "fecha_descarga",
    "licencia", "url_licencia", "atribucion", "sha256",
)  # fmt: skip


def source_citation(row: dict[str, str]) -> dict[str, str]:
    """Datos para citar la fuente y la fecha en cualquier salida (aviso legal del Congreso)."""
    cited = {k: row[k] for k in CITED_FIELDS}
    cited["cita"] = (
        f"{row['atribucion']}. Sesión del {row['fecha_evento']}. "
        f"Fecha de última actualización consultada: {row['fecha_descarga']}."
    )
    return cited


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--manifest", type=Path, default=None)
    args = parser.parse_args(argv)

    data_dir = Path(os.environ.get("DATA_DIR") or "data")
    try:
        row = require_ready(args.video, args.manifest or data_dir / "manifiesto.csv")
    except ManifestError as exc:
        raise SystemExit(str(exc)) from exc

    out_dir = data_dir / "processed" / args.video.stem
    wav = extract_audio(args.video, out_dir / "audio.wav")
    segments = transcribe(wav, TranscribeConfig.from_env())
    turns = diarize(wav, DiarizeConfig.from_env())
    timeline = build_timeline(args.video.stem, wav_duration_s(wav), segments, turns)
    (out_dir / "source.json").write_text(
        json.dumps(source_citation(row), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    for path in write_outputs(timeline, out_dir):
        print(path)


if __name__ == "__main__":
    main()
