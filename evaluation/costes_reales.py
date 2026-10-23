"""Tabla del coste real medido por sesión en docs/HERRAMIENTAS_Y_COSTES.md.

Uso: python -m evaluation.costes_reales [--data data] [--doc docs/HERRAMIENTAS_Y_COSTES.md]

Lee `data/processed/*/coste.json` (los escribe `pipeline.sesion`) y reescribe la tabla entre las
marcas `<!-- costes-reales:inicio -->` y `<!-- costes-reales:fin -->` del documento. Las cifras las
calcula el código; el documento solo las muestra.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

START, END = "<!-- costes-reales:inicio -->", "<!-- costes-reales:fin -->"


def _eur(v) -> str:
    return "-" if v is None else f"{v:.4f} €".replace(".", ",")


def table(processed: Path) -> str:
    rows = [
        "| Sesión | Tiempo total | Qwen (llamadas / tokens) | Máquina | Qwen | **Total sin IVA** |",
        "|---|---|---|---|---|---|",
    ]
    for f in sorted(processed.glob("*/coste.json")):
        c = json.loads(f.read_text("utf-8"))
        tokens = f"{c['qwen_llamadas']} / {c['qwen_tokens_in'] + c['qwen_tokens_out']}"
        rows.append(
            f"| {f.parent.name} | {c['segundos_totales'] / 60:.0f} min | {tokens} | "
            f"{_eur(c.get('maquina_eur'))} | {_eur(c.get('qwen_eur'))} | "
            f"**{_eur(c.get('total_eur'))}** |"
        )
    if len(rows) == 2:
        rows.append("| (aún no hay sesiones medidas) | | | | | |")
    return "\n".join(rows)


def update(doc: Path, processed: Path) -> None:
    text = doc.read_text("utf-8")
    block = f"{START}\n{table(processed)}\n{END}"
    if START in text and END in text:
        text = text[: text.index(START)] + block + text[text.index(END) + len(END) :]
    else:
        text = text.rstrip("\n") + "\n\n## Coste real medido por sesión\n\n" + block + "\n"
    doc.write_text(text, "utf-8")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", type=Path, default=Path("data"))
    ap.add_argument("--doc", type=Path, default=Path("docs/HERRAMIENTAS_Y_COSTES.md"))
    args = ap.parse_args(argv)
    update(args.doc, args.data / "processed")
    print(f"tabla actualizada en {args.doc}")


if __name__ == "__main__":
    main()
