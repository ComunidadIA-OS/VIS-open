"""Guarda en disco el informe y la transcripción (CSV) de cada sesión.

Uso: python -m dashboard.export [--data data] [--out data/informes] [--link-base URL]
El informe enlaza a `transcripcion_<id>.csv`; con `--link-base` el enlace apunta a esa URL (por
ejemplo un almacenamiento privado donde se suba el CSV). Salida en `data/`: no se sube al repo.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from dashboard.data import export_session, load_sessions


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
