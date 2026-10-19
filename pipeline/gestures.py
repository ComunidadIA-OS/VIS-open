"""Detector de mano levantada a partir de puntos del cuerpo (PROTOTIPO).

Funciones puras: reciben los puntos de pose (p. ej. de MediaPipe Pose) y no tocan imagen,
cara ni identidad. Sin reconocimiento facial. Una persona = un conjunto de puntos anónimo.

Convención MediaPipe Pose: coordenadas normalizadas, `y` crece hacia abajo; índices
11/12 = hombro izquierdo/derecho, 15/16 = muñeca izquierda/derecha.
Regla: mano levantada si la muñeca está por encima del hombro del mismo lado
(`wrist.y < shoulder.y - margin`) y ambos puntos son visibles.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
LEFT_WRIST, RIGHT_WRIST = 15, 16


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    visibility: float = 1.0


Pose = Mapping[int, Point]


def raised_hands(pose: Pose, margin: float = 0.05, min_visibility: float = 0.5) -> set[str]:
    """Lados con la mano levantada en un fotograma: subconjunto de {'left', 'right'}."""
    sides = {"left": (LEFT_SHOULDER, LEFT_WRIST), "right": (RIGHT_SHOULDER, RIGHT_WRIST)}
    out = set()
    for side, (sh_i, wr_i) in sides.items():
        sh, wr = pose.get(sh_i), pose.get(wr_i)
        if sh is None or wr is None:
            continue
        if min(sh.visibility, wr.visibility) < min_visibility:
            continue
        if wr.y < sh.y - margin:
            out.add(side)
    return out


def detect_raises(
    frames: Sequence[Pose | None],
    fps: float,
    min_duration_s: float = 1.0,
    max_gap_frames: int = 2,
    margin: float = 0.05,
    min_visibility: float = 0.5,
) -> list[tuple[float, float]]:
    """Intervalos (inicio_s, fin_s) con una mano levantada de forma sostenida.

    Un fotograma `None` (persona no detectada) o hasta `max_gap_frames` fotogramas sueltos sin
    mano levantada no cortan el gesto. Gestos más cortos que `min_duration_s` se descartan.
    """
    if fps <= 0:
        raise ValueError("fps debe ser > 0")
    hits = [bool(f) and bool(raised_hands(f, margin, min_visibility)) for f in frames]
    intervals: list[tuple[int, int]] = []
    start = last = None
    for i, hit in enumerate(hits):
        if hit:
            if start is None:
                start = i
            last = i
        elif start is not None and i - last > max_gap_frames:
            intervals.append((start, last))
            start = None
    if start is not None:
        intervals.append((start, last))
    return [
        (round(a / fps, 3), round((b + 1) / fps, 3))
        for a, b in intervals
        if (b + 1 - a) / fps >= min_duration_s
    ]
