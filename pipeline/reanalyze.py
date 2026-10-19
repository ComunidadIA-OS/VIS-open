"""Vuelve a aplicar seudonimización, género por lenguaje y resumen sobre una sesión ya procesada.

Uso: python -m pipeline.reanalyze data/processed/V001
Sirve cuando cambian las reglas y no hace falta volver a transcribir. Sobrescribe `timeline.json`,
`resumen.json` y `review_genero.csv` de esa carpeta.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from contracts import AnalysisTimeline, ReviewRow, write_rows
from pipeline.analyze import analyze_timeline


def reanalyze(folder: Path) -> list[Path]:
    folder = Path(folder)
    timeline = AnalysisTimeline.model_validate_json((folder / "timeline.json").read_text("utf-8"))
    timeline, review, summary = analyze_timeline(timeline)
    out = [folder / "timeline.json", folder / "resumen.json", folder / "review_genero.csv"]
    out[0].write_text(timeline.model_dump_json(indent=2), encoding="utf-8")
    out[1].write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    write_rows(review, ReviewRow, out[2])
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    for path in reanalyze(parser.parse_args(argv).folder):
        print(path)


if __name__ == "__main__":
    main()
