"""Guarda en disco el informe (PDF) y la transcripción (CSV) de cada sesión.

Uso: python -m dashboard.export [--data data] [--out data/informes] [--link-base URL]
El informe enlaza a `transcripcion_<id>.csv`; con `--link-base` el enlace apunta a esa URL (por
ejemplo un almacenamiento privado donde se suba el CSV). Salida en `data/`: no se sube al repo.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from dashboard.data import Session, load_sessions, transcript_csv
from dashboard.pdf_report import report_pdf


def export_session(session: Session, out_dir: Path, link_base: str | None = None) -> list[Path]:
    """Guarda `informe_<id>.pdf` y `transcripcion_<id>.csv`; el informe enlaza al CSV."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_name = f"transcripcion_{session.session_id}.csv"
    link = f"{link_base.rstrip('/')}/{csv_name}" if link_base else csv_name
    report = out_dir / f"informe_{session.session_id}.pdf"
    report.write_bytes(report_pdf(session, link))
    table = out_dir / csv_name
    table.write_text(transcript_csv(session), encoding="utf-8")
    return [report, table]


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", type=Path, default=Path("data"))
    ap.add_argument("--out", type=Path, default=Path("data/informes"))
    ap.add_argument("--link-base", default=None)
    args = ap.parse_args(argv)
    for session in load_sessions(args.data):
        for path in export_session(session, args.out, args.link_base):
            print(path)


if __name__ == "__main__":
    main()
