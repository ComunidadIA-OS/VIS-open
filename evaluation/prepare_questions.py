"""Hoja para anotar preguntas (M09) en un tramo de una sesión, y datos para el ajuste de Qwen.

1) Hoja de anotación (Ivette): los turnos de un tramo, EN ORDEN del vídeo, sin ninguna etiqueta
   del sistema, para que marque si cada uno formula una pregunta:
     python -m evaluation.prepare_questions hoja --sesion V004 --desde 0:10:00 --hasta 0:30:00
   Escribe `data/anotacion/preguntas_para_anotar.csv` con
   `turn_id,t_inicio,context_before,text,es_pregunta` (`es_pregunta` vacío: si | no) y, opcional,
   `frase` (la frase que formula la pregunta, si quiere indicarla).

2) Datos de ajuste (Sabrina): con la hoja ya anotada, escribe los JSONL de entrenamiento y de
   evaluación en el formato cerrado que usa el motor (`decision/questions.py`):
     python -m evaluation.prepare_questions ajuste --train a.csv --eval b.csv
   La evaluación va con OTRA sesión (si no se da, se separa una fracción). Solo texto seudonimizado;
   `data/` no se sube al repo y el modelo ajustado tampoco se publica.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections.abc import Sequence
from pathlib import Path

from contracts import AnalysisTimeline
from dashboard.data import fmt_time
from decision.questions import QUESTION_PROMPT, QuestionRulesEngine
from evaluation.prepare_annotation import build_turns
from evaluation.questions_eval import read_rows
from sources.manifest import parse_hms

SHEET_COLUMNS = ["turn_id", "t_inicio", "context_before", "text", "es_pregunta", "frase"]


def write_sheet(timeline: AnalysisTimeline, start_s: float, end_s: float, out: Path) -> int:
    turns = [
        t
        for t in build_turns(timeline)
        if start_s <= t.start_s < end_s and len(t.text.split()) >= 4
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(SHEET_COLUMNS)
        for i, t in enumerate(turns, 1):
            w.writerow([f"Q{i:03d}", fmt_time(t.start_s), t.context_before, t.text, "", ""])
    return len(turns)


def _example(row: dict[str, str]) -> dict | None:
    """Una conversación (sistema, usuario, asistente) con la respuesta cerrada de la anotadora."""
    text = row["text"]
    asked = row["es_pregunta"] == "si"
    evidence = None
    if asked:
        phrase = (row.get("frase") or "").strip()
        evidence = phrase or QuestionRulesEngine().ask(text).evidence
        if not evidence or evidence.lower() not in text.lower():
            return None  # sin frase literal no hay respuesta válida: se anota aparte
    marker = "ajuste"
    data = f"[CONTEXTO]\n{row.get('context_before') or ''}\n[TURNO]\n{text}"
    answer = {
        "is_question": asked,
        "confidence": 1.0,
        "evidence": evidence,
        "reason": "anotación humana",
    }
    return {
        "messages": [
            {"role": "system", "content": QUESTION_PROMPT.format(nonce=marker)},
            {"role": "user", "content": f"<DATOS-{marker}>\n{data}\n</DATOS-{marker}>"},
            {"role": "assistant", "content": json.dumps(answer, ensure_ascii=False)},
        ]
    }


def build_finetune(
    train_csvs: Sequence[Path],
    eval_csvs: Sequence[Path],
    out_dir: Path,
    eval_fraction: float,
    seed: int,
) -> dict[str, int]:
    train_rows = [r for p in train_csvs for r in read_rows(p)]
    eval_rows = [r for p in eval_csvs for r in read_rows(p)]
    if not eval_rows:  # sin sesión de evaluación aparte: se separa una fracción (peor opción)
        rng = random.Random(seed)
        rng.shuffle(train_rows)
        cut = max(1, int(len(train_rows) * eval_fraction))
        eval_rows, train_rows = train_rows[:cut], train_rows[cut:]
    out_dir.mkdir(parents=True, exist_ok=True)
    stats = {}
    for name, rows in (("train", train_rows), ("eval", eval_rows)):
        examples = [e for r in rows if (e := _example(r))]
        with (out_dir / f"{name}.jsonl").open("w", encoding="utf-8") as fh:
            for e in examples:
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")
        stats[name] = len(examples)
        stats[f"{name}_sin_frase"] = len(rows) - len(examples)
    return stats


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("hoja", help="hoja de anotación de un tramo")
    h.add_argument("--sesion", required=True)
    h.add_argument("--desde", default="0:00:00")
    h.add_argument("--hasta", default="0:20:00")
    h.add_argument("--data", type=Path, default=Path("data"))
    h.add_argument("--out", type=Path, default=Path("data/anotacion/preguntas_para_anotar.csv"))
    a = sub.add_parser("ajuste", help="JSONL de entrenamiento y evaluación")
    a.add_argument("--train", type=Path, nargs="+", required=True)
    a.add_argument("--eval", type=Path, nargs="*", default=[])
    a.add_argument("--out", type=Path, default=Path("data/finetune"))
    a.add_argument("--eval-fraction", type=float, default=0.2)
    a.add_argument("--seed", type=int, default=7)
    args = ap.parse_args(argv)
    if args.cmd == "hoja":
        path = args.data / "processed" / args.sesion / "timeline.json"
        timeline = AnalysisTimeline.model_validate_json(path.read_text("utf-8"))
        n = write_sheet(timeline, parse_hms(args.desde), parse_hms(args.hasta), args.out)
        print(f"{n} turnos -> {args.out}")
    else:
        print(build_finetune(args.train, args.eval, args.out, args.eval_fraction, args.seed))


if __name__ == "__main__":
    main()
