"""Mide un detector de preguntas contra una anotación hecha a mano (el antes y el después de M09).

CSV (UTF-8), una fila por turno:
  turn_id         identificador único
  text            texto (seudonimizado) del turno
  context_before  (opcional) lo dicho justo antes
  es_pregunta     si | no                           (la anotación de Ivette)

Uso: python -m evaluation.questions_eval anotadas.csv --engines rules,llm [--out resultados.json]
Da precisión, cobertura (recall) y F1 de la clase «pregunta», la matriz de confusión, el % a
revisión y, si el motor usa API, los tokens. Con datos sintéticos solo se prueba la mecánica:
la anotación real es de Ivette y no se sube al repo.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Sequence
from pathlib import Path
from statistics import mean

from decision.questions import get_question_engine
from pipeline.envfile import load_dotenv

REQUIRED = ["turn_id", "text", "es_pregunta"]
YES, NO = "si", "no"


def read_rows(path: Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"faltan columnas: {missing}")
        rows, seen = [], set()
        for n, row in enumerate(reader, start=2):
            label = (row["es_pregunta"] or "").strip().lower()
            if label not in (YES, NO):
                raise ValueError(f"fila {n}: es_pregunta '{label}' no válida; admitidas: si, no")
            if row["turn_id"] in seen:
                raise ValueError(f"fila {n}: turn_id repetido '{row['turn_id']}'")
            seen.add(row["turn_id"])
            rows.append({**row, "es_pregunta": label})
        return rows


def question_report(gold: Sequence[bool], pred: Sequence[bool]) -> dict:
    tp = sum(g and p for g, p in zip(gold, pred, strict=True))
    fp = sum((not g) and p for g, p in zip(gold, pred, strict=True))
    fn = sum(g and (not p) for g, p in zip(gold, pred, strict=True))
    tn = len(gold) - tp - fp - fn
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round((tp + tn) / len(gold), 4) if gold else 0.0,
        "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
    }


def evaluate(engine, rows: Sequence[dict[str, str]]) -> dict:
    gold = [r["es_pregunta"] == YES for r in rows]
    decisions = [engine.ask(r["text"], r.get("context_before") or None) for r in rows]
    report = question_report(gold, [d.is_question for d in decisions])
    billed = [d for d in decisions if d.tokens_in is not None]
    return {
        "engine": engine.name,
        "n": len(rows),
        **report,
        "errores": sum(d.error is not None for d in decisions),
        "revision_%": round(
            100 * mean(d.error is not None or d.confidence < 0.7 for d in decisions), 1
        )
        if decisions
        else 0.0,
        "latencia_media_s": round(mean(d.latency_s or 0.0 for d in decisions), 4)
        if decisions
        else 0.0,
        "tokens_in": sum(d.tokens_in or 0 for d in billed),
        "tokens_out": sum(d.tokens_out or 0 for d in billed),
    }


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("csv", type=Path)
    ap.add_argument("--engines", default="rules")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    load_dotenv()
    rows = read_rows(args.csv)
    results = [evaluate(get_question_engine(n.strip()), rows) for n in args.engines.split(",")]
    for r in results:
        print(
            f"{r['engine']}: F1 {r['f1']:.2f} (precisión {r['precision']:.2f}, "
            f"cobertura {r['recall']:.2f}); {r['errores']} errores sobre {r['n']} turnos"
        )
    if args.out:
        args.out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
