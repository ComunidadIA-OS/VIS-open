"""WER (transcripción) y DER (diarización) contra una referencia hecha a mano.

- WER: distancia de edición entre palabras (sustituciones, borrados e inserciones) / palabras de la
  referencia. Se normaliza: minúsculas, sin signos de puntuación; las tildes cuentan.
- DER: (voz perdida + falsa alarma + confusión de hablante) / voz de la referencia, sobre una
  rejilla de 10 ms, sin margen de tolerancia («collar» 0): más estricto que el estándar de 0,25 s.
  Los hablantes de la hipótesis se emparejan con los de la referencia de la forma óptima. Con
  habla solapada, cada instante cuenta tantos hablantes como estén activos.

Formatos (UTF-8, sin nombres):
  texto:   .txt con la transcripción
  turnos:  .csv con `speaker_id,start_s,end_s`
Uso: python -m evaluation.asr_diar wer ref.txt hip.txt
     python -m evaluation.asr_diar der ref.csv hip.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections.abc import Sequence
from pathlib import Path

import numpy as np

Segment = tuple[str, float, float]  # (hablante, inicio_s, fin_s)
STEP_S = 0.01
_MAX_MAPPED = 20  # la asignación óptima es 2^n; con más hablantes pedimos recortar


def _words(text: str) -> list[str]:
    return re.sub(r"[^\w\s]|_", " ", text.lower()).split()


def wer(reference: str, hypothesis: str) -> dict:
    ref, hyp = _words(reference), _words(hypothesis)
    if not ref:
        raise ValueError("la referencia no tiene palabras")
    # d[i][j] = (coste, sustituciones, borrados, inserciones) para ref[:i] y hyp[:j]
    prev = [(j, 0, 0, j) for j in range(len(hyp) + 1)]
    for i, r in enumerate(ref, 1):
        cur = [(i, 0, i, 0)]
        for j, h in enumerate(hyp, 1):
            c, s, d, n = prev[j - 1]
            options = [(c + (r != h), s + (r != h), d, n)]
            c, s, d, n = prev[j]
            options.append((c + 1, s, d + 1, n))
            c, s, d, n = cur[j - 1]
            options.append((c + 1, s, d, n + 1))
            cur.append(min(options, key=lambda o: o[0]))
        prev = cur
    cost, sub, dele, ins = prev[-1]
    return {
        "wer": round(cost / len(ref), 4),
        "sustituciones": sub,
        "borrados": dele,
        "inserciones": ins,
        "palabras_referencia": len(ref),
    }


def _activity(segments: Sequence[Segment], n_frames: int) -> dict[str, np.ndarray]:
    out: dict[str, np.ndarray] = {}
    for speaker, start, end in segments:
        if end < start or start < 0:
            raise ValueError(f"turno no válido: {speaker} {start}-{end}")
        mask = out.setdefault(speaker, np.zeros(n_frames, dtype=bool))
        mask[int(round(start / STEP_S)) : int(round(end / STEP_S))] = True
    return out


def _best_assignment(overlap: np.ndarray) -> int:
    """Máxima suma de solapes con cada hablante de la hipótesis usado una vez (DP por bits)."""
    n_ref, n_hyp = overlap.shape
    best = {0: 0.0}
    for i in range(n_ref):
        nxt = dict(best)  # la fila i puede quedarse sin pareja
        for used, value in best.items():
            for j in range(n_hyp):
                if not used >> j & 1:
                    key = used | 1 << j
                    nxt[key] = max(nxt.get(key, -1.0), value + overlap[i, j])
        best = nxt
    return int(max(best.values()))


def der(reference: Sequence[Segment], hypothesis: Sequence[Segment]) -> dict:
    if not reference:
        raise ValueError("la referencia no tiene turnos")
    end = max(e for _, _, e in [*reference, *hypothesis])
    n_frames = int(round(end / STEP_S)) + 1
    ref, hyp = _activity(reference, n_frames), _activity(hypothesis, n_frames)
    if min(len(ref), len(hyp)) > _MAX_MAPPED:
        raise ValueError(f"demasiados hablantes para emparejar (máximo {_MAX_MAPPED})")
    n_ref = np.sum(list(ref.values()), axis=0)
    n_hyp = np.sum(list(hyp.values()), axis=0) if hyp else np.zeros(n_frames, dtype=int)
    overlap = np.array([[int(np.sum(r & h)) for h in hyp.values()] for r in ref.values()])
    correct = _best_assignment(overlap) if overlap.size else 0
    ref_total = int(n_ref.sum())
    missed = int(np.maximum(n_ref - n_hyp, 0).sum())
    false_alarm = int(np.maximum(n_hyp - n_ref, 0).sum())
    confusion = int(np.minimum(n_ref, n_hyp).sum()) - correct
    return {
        "der": round((missed + false_alarm + confusion) / ref_total, 4),
        "voz_perdida": round(missed / ref_total, 4),
        "falsa_alarma": round(false_alarm / ref_total, 4),
        "confusion": round(confusion / ref_total, 4),
        "voz_referencia_s": round(ref_total * STEP_S, 2),
    }


def read_segments(path: Path) -> list[Segment]:
    with Path(path).open(newline="", encoding="utf-8") as fh:
        return [
            (row["speaker_id"], float(row["start_s"]), float(row["end_s"]))
            for row in csv.DictReader(fh)
        ]


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("metric", choices=["wer", "der"])
    ap.add_argument("reference", type=Path)
    ap.add_argument("hypothesis", type=Path)
    args = ap.parse_args(argv)
    if args.metric == "wer":
        result = wer(
            args.reference.read_text(encoding="utf-8"), args.hypothesis.read_text(encoding="utf-8")
        )
    else:
        result = der(read_segments(args.reference), read_segments(args.hypothesis))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
