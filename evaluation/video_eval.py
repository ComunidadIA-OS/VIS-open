"""Evaluación del vídeo contra una anotación hecha a mano (qué tan bien medimos).

Tres preguntas de la charla de visión, aplicadas a VIS Open:
1. ¿Se encuentran las personas?  -> `evaluate_counts` (error de conteo y sesgo a contar de menos).
2. ¿Las manos levantadas?        -> `evaluate_hands` (precisión, recall y F1 por solape temporal).
3. ¿El atributo es correcto?     -> `evaluate_track_genders` (género por audio de cada pista, con
   «desconocido» contado aparte: cuántas mujeres y hombres quedan sin etiquetar).

Formatos de anotación (CSV UTF-8, sin nombres):
  personas.csv:  t_s,n_personas              (cuántas personas se ven en ese segundo)
  manos.csv:     zona,inicio_s,fin_s         (cada mano levantada, con su zona Z1..Z4)
  pistas.csv:    pista,genero                (mujer | hombre | desconocido, para cada pista)
Uso: python -m evaluation.video_eval data/processed/V001/video.json --personas p.csv
     --manos m.csv --pistas t.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Sequence
from pathlib import Path
from statistics import mean

from evaluation.benchmark import CLASSES, f1_report


def _rows(path: Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def evaluate_counts(
    predicted: Sequence[Sequence[float]],
    gold: Sequence[tuple[float, int]],
    tolerance_s: float = 0.5,
) -> dict:
    """Empareja cada anotación con el fotograma más cercano (<= tolerancia) y mide el error.

    `bias` < 0 = se cuenta de menos. `recall` y `precision` son sobre personas (mínimo entre lo
    detectado y lo real en cada instante): aproximación, sin emparejar caja por caja.
    """
    pairs = []
    for t, truth in gold:
        near = min(predicted, key=lambda p: abs(p[0] - t), default=None)
        if near is not None and abs(near[0] - t) <= tolerance_s:
            pairs.append((int(near[1]), int(truth)))
    if not pairs:
        return {"n": 0}
    hit = sum(min(p, g) for p, g in pairs)
    gold_total = sum(g for _, g in pairs)
    pred_total = sum(p for p, _ in pairs)
    return {
        "n": len(pairs),
        "mae": round(mean(abs(p - g) for p, g in pairs), 3),
        "bias": round(mean(p - g for p, g in pairs), 3),
        "exact_%": round(100 * mean(p == g for p, g in pairs), 1),
        "recall": round(hit / gold_total, 3) if gold_total else None,
        "precision": round(hit / pred_total, 3) if pred_total else None,
    }


def _overlap(a: tuple[float, float], b: tuple[float, float]) -> float:
    inter = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
    union = (a[1] - a[0]) + (b[1] - b[0]) - inter
    return inter / union if union > 0 else 0.0


def evaluate_hands(
    predicted: Sequence[dict],
    gold: Sequence[dict],
    min_iou: float = 0.3,
    same_zone: bool = True,
) -> dict:
    """Empareja manos detectadas y anotadas por solape en el tiempo (y zona): P, R y F1."""
    used: set[int] = set()
    tp = 0
    for g in gold:
        best = max(
            (
                (_overlap((g["inicio_s"], g["fin_s"]), (p["inicio_s"], p["fin_s"])), i)
                for i, p in enumerate(predicted)
                if i not in used and (not same_zone or p["zona"] == g["zona"])
            ),
            default=(0.0, -1),
        )
        if best[0] >= min_iou:
            used.add(best[1])
            tp += 1
    prec = tp / len(predicted) if predicted else 0.0
    rec = tp / len(gold) if gold else 0.0
    return {
        "anotadas": len(gold),
        "detectadas": len(predicted),
        "aciertos": tp,
        "precision": round(prec, 3),
        "recall": round(rec, 3),
        "f1": round(2 * prec * rec / (prec + rec), 3) if prec + rec else 0.0,
    }


def evaluate_track_genders(predicted: dict[int, str], gold: dict[int, str]) -> dict:
    """Género de las pistas (por audio) frente a la anotación.

    «desconocido» se cuenta aparte: no es acierto ni error, pero se informa. El sesgo está en
    cuántas mujeres lo reciben frente a cuántos hombres.
    """
    common = [t for t in gold if t in predicted]
    if not common:
        return {"n": 0}
    labelled = [t for t in common if predicted[t] != "desconocido"]
    correct = [t for t in labelled if predicted[t] == gold[t]]
    groups = ("mujer", "hombre")
    unknown_of = {
        g: sum(1 for t in common if gold[t] == g and predicted[t] == "desconocido") for g in groups
    }
    total_of = {g: sum(1 for t in common if gold[t] == g) for g in groups}
    return {
        "n": len(common),
        "etiquetadas_%": round(100 * len(labelled) / len(common), 1),
        "acierto_sobre_etiquetadas_%": (
            round(100 * len(correct) / len(labelled), 1) if labelled else None
        ),
        "sin_etiquetar_por_genero": {g: f"{unknown_of[g]} de {total_of[g]}" for g in groups},
        "f1": (
            f1_report([gold[t] for t in common], [predicted[t] for t in common])
            if set(gold.values()) <= set(CLASSES)
            else None
        ),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video_json", type=Path)
    parser.add_argument("--personas", type=Path)
    parser.add_argument("--manos", type=Path)
    parser.add_argument("--pistas", type=Path)
    args = parser.parse_args(argv)
    video = json.loads(args.video_json.read_text(encoding="utf-8"))
    report = {}
    if args.personas:
        gold = [(float(r["t_s"]), int(r["n_personas"])) for r in _rows(args.personas)]
        report["personas"] = evaluate_counts(video["personas_por_fotograma"], gold)
    if args.manos:
        gold_h = [
            {"zona": r["zona"], "inicio_s": float(r["inicio_s"]), "fin_s": float(r["fin_s"])}
            for r in _rows(args.manos)
        ]
        report["manos"] = evaluate_hands(video["manos_levantadas"], gold_h)
    if args.pistas:
        pred = {t["pista"]: t["genero_por_audio"] for t in video["pistas"]}
        gold_t = {int(r["pista"]): r["genero"] for r in _rows(args.pistas)}
        report["genero_pistas"] = evaluate_track_genders(pred, gold_t)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
