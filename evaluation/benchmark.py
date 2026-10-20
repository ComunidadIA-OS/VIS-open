"""Compara motores de decisión sobre un CSV anotado: F1 por clase, matriz de confusión, latencia.

CSV (UTF-8), una fila por turno:
  turn_id         identificador único
  text            texto del turno
  context_before  (opcional) lo dicho justo antes, p. ej. la Presidencia dando la palabra
  label           mujer | hombre | desconocido   (la etiqueta de las anotadoras)

Uso: python -m evaluation.benchmark turnos.csv --engines rules,llm [--out resultados.json]
Con datos sintéticos solo se prueba la mecánica: los 150 turnos reales los anotan Ivette y Veru.
Nunca se suben turnos reales al repo.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Sequence
from pathlib import Path
from statistics import mean

from decision.engine import DecisionEngine, Turn, get_engine
from evaluation.cost import Prices, usage_report
from pipeline.envfile import load_dotenv

CLASSES = ["mujer", "hombre", "desconocido"]
REQUIRED_COLUMNS = ["turn_id", "text", "label"]


def read_turns(path: Path) -> list[tuple[Turn, str]]:
    with Path(path).open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"faltan columnas: {missing}")
        out, seen = [], set()
        for n, row in enumerate(reader, start=2):
            label = (row["label"] or "").strip()
            if label not in CLASSES:
                raise ValueError(f"fila {n}: label '{label}' no válida; admitidas: {CLASSES}")
            if row["turn_id"] in seen:
                raise ValueError(f"fila {n}: turn_id repetido '{row['turn_id']}'")
            seen.add(row["turn_id"])
            turn = Turn(
                turn_id=row["turn_id"],
                text=row["text"],
                context_before=row.get("context_before") or None,
            )
            out.append((turn, label))
        return out


def f1_report(gold: Sequence[str], pred: Sequence[str]) -> dict:
    """Precisión, recall y F1 por clase, F1 macro, exactitud y matriz de confusión."""
    confusion = {g: {p: 0 for p in CLASSES} for g in CLASSES}
    for g, p in zip(gold, pred, strict=True):
        confusion[g][p] += 1
    per_class = {}
    for c in CLASSES:
        tp = confusion[c][c]
        fp = sum(confusion[g][c] for g in CLASSES if g != c)
        fn = sum(confusion[c][p] for p in CLASSES if p != c)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per_class[c] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": tp + fn,
        }
    n = len(gold)
    return {
        "per_class": per_class,
        "f1_macro": round(mean(v["f1"] for v in per_class.values()), 4),
        "accuracy": round(sum(confusion[c][c] for c in CLASSES) / n, 4) if n else 0.0,
        "confusion": confusion,
    }


def evaluate(
    engine: DecisionEngine,
    turns: Sequence[tuple[Turn, str]],
    decisions_out: list | None = None,
) -> dict:
    decisions = [engine.decide(t) for t, _ in turns]
    if decisions_out is not None:
        decisions_out.extend(decisions)
    gold = [label for _, label in turns]
    report = f1_report(gold, [d.gender for d in decisions])
    latencies = [d.latency_s for d in decisions if d.latency_s is not None]
    report.update(
        engine=engine.name,
        n=len(turns),
        review_rate=round(sum(d.needs_review for d in decisions) / len(turns), 4) if turns else 0.0,
        errors=sum(d.error is not None for d in decisions),
        latency_mean_s=round(mean(latencies), 4) if latencies else None,
        coste=usage_report(decisions, Prices.from_env()),
    )
    return report


DETAIL_COLUMNS = [
    "turn_id", "label", "pred", "acierto", "confianza", "error", "reason",
    "tokens_in", "tokens_out", "latencia_s", "evidence", "context_before", "text",
]  # fmt: skip


def write_detail(path: Path, turns: Sequence[tuple[Turn, str]], decisions: Sequence) -> None:
    """Una fila por turno con lo que decidió el motor. Lleva el texto de los turnos: no se sube."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=DETAIL_COLUMNS)
        writer.writeheader()
        for (turn, label), d in zip(turns, decisions, strict=True):
            writer.writerow(
                {
                    "turn_id": turn.turn_id, "label": label, "pred": d.gender,
                    "acierto": int(d.gender == label), "confianza": d.confidence,
                    "error": d.error or "", "reason": d.reason or "",
                    "tokens_in": d.tokens_in, "tokens_out": d.tokens_out,
                    "latencia_s": d.latency_s, "evidence": d.evidence or "",
                    "context_before": turn.context_before or "", "text": turn.text,
                }
            )  # fmt: skip


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--engines", default="rules")
    parser.add_argument("--out", type=Path)
    parser.add_argument(
        "--detalle", type=Path, help="carpeta donde guardar la decisión de cada turno (CSV)"
    )
    args = parser.parse_args(argv)
    load_dotenv()  # LLM_MODEL, LLM_API_KEY, precios...

    turns = read_turns(args.csv)
    results = []
    for name in args.engines.split(","):
        decisions: list = []
        results.append(evaluate(get_engine(name.strip()), turns, decisions))
        if args.detalle:
            write_detail(args.detalle / f"detalle_{name.strip()}.csv", turns, decisions)
    for r in results:
        per = ", ".join(f"{c} {v['f1']:.2f}" for c, v in r["per_class"].items())
        print(
            f"{r['engine']}: F1 macro {r['f1_macro']:.2f} ({per}); revisión {r['review_rate']:.0%}"
        )
    if args.out:
        args.out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
