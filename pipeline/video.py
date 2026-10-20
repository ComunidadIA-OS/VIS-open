"""Vídeo: personas visibles y manos levantadas con puntos de pose (MediaPipe). PROTOTIPO.

Una sola pasada sobre fotogramas muestreados (por defecto 2 por segundo): en cada uno, MediaPipe
Pose Landmarker devuelve los puntos del cuerpo de cada persona visible. De ahí salen:
- personas visibles por fotograma (y su máximo y mediana), y
- manos levantadas (muñeca por encima del hombro, `pipeline.gestures`), asignadas a una zona
  horizontal de la imagen (Z1..Zn), no a una persona concreta.

Reglas: sin reconocimiento facial, sin identificar a nadie, sin guardar imágenes ni fotogramas.
Solo se escriben números. Límites: es una estimación de lo que ve la cámara, no de quién hay en
la sala; con planos amplios las personas pequeñas no se detectan (cuenta de menos), y cuando la
cámara cambia de plano o se mueve, las zonas no son comparables entre planos.

Uso: python -m pipeline.video data/raw/V001.mp4 [--model ruta/pose_landmarker.task]
(el modelo también puede venir de POSE_MODEL en el `.env`; no se incluye en el repositorio).
"""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median

from pipeline.envfile import load_dotenv
from pipeline.gestures import LEFT_SHOULDER, RIGHT_SHOULDER, Point, Pose, raised_hands

ZONES = 4  # franjas horizontales de la imagen
SAMPLE_FPS = 2.0
NUM_POSES = 30  # máximo de personas por fotograma que pide a MediaPipe
PoseDetector = Callable[[object], Sequence[Pose]]  # fotograma RGB -> poses (una por persona)


@dataclass(frozen=True)
class FrameResult:
    t_s: float
    n_people: int
    raised: list[tuple[str, str]] = field(default_factory=list)  # (zona, lado)


def zone_of(pose: Pose, zones: int = ZONES) -> str:
    """Zona horizontal (Z1 izquierda … Zn derecha) según el punto medio de los hombros."""
    xs = [pose[i].x for i in (LEFT_SHOULDER, RIGHT_SHOULDER) if i in pose]
    x = sum(xs) / len(xs) if xs else 0.5
    return f"Z{min(zones, max(1, int(x * zones) + 1))}"


def analyze_frames(
    frames: Iterable[tuple[float, object]], detect: PoseDetector, **kw
) -> list[FrameResult]:
    """Aplica `detect` a cada (t_s, fotograma) y resume personas y manos levantadas."""
    out = []
    for t_s, frame in frames:
        poses = list(detect(frame))
        raised = [(zone_of(p), side) for p in poses for side in sorted(raised_hands(p, **kw))]
        out.append(FrameResult(round(t_s, 3), len(poses), raised))
    return out


def summarize(results: Sequence[FrameResult], min_raise_s: float = 1.0) -> dict:
    """Cifras del vídeo: personas visibles y manos levantadas sostenidas por zona."""
    if not results:
        return {"n_fotogramas": 0}
    counts = [r.n_people for r in results]
    step = (
        median(b.t_s - a.t_s for a, b in zip(results, results[1:], strict=False))
        if len(results) > 1
        else 0
    )
    # una mano levantada = racha de fotogramas consecutivos con (zona, lado) levantado
    zones: dict[str, list[tuple[float, float]]] = {}
    open_runs: dict[tuple[str, str], list[float]] = {}
    for r in results:
        now = set(r.raised)
        for key in list(open_runs):
            if key not in now:
                start, end = open_runs.pop(key)
                if end - start + step >= min_raise_s:
                    zones.setdefault(key[0], []).append((start, end + step))
        for key in now:
            open_runs.setdefault(key, [r.t_s, r.t_s])[1] = r.t_s
    for key, (start, end) in open_runs.items():
        if end - start + step >= min_raise_s:
            zones.setdefault(key[0], []).append((start, end + step))
    return {
        "aviso": (
            "Estimación de lo que ve la cámara, no de quién hay en la sala; sin caras ni "
            "identificación; en planos amplios se cuenta de menos."
        ),
        "n_fotogramas": len(results),
        "personas_visibles_max": max(counts),
        "personas_visibles_mediana": float(median(counts)),
        "fotogramas_sin_personas_%": round(100 * counts.count(0) / len(counts), 1),
        "manos_levantadas_por_zona": {z: len(v) for z, v in sorted(zones.items())},
        "manos_levantadas": [
            {"zona": z, "inicio_s": round(a, 2), "fin_s": round(b, 2)}
            for z, v in sorted(zones.items())
            for a, b in v
        ],
    }


def iter_video_frames(video: Path, sample_fps: float = SAMPLE_FPS):
    """(t_s, fotograma RGB) con `sample_fps` fotogramas por segundo (OpenCV)."""
    import cv2

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError(f"no se puede abrir el vídeo {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    every = max(1, round(fps / sample_fps))
    i = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if i % every == 0:
                yield i / fps, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            i += 1
    finally:
        cap.release()


def mediapipe_detector(model_path: Path, num_poses: int = NUM_POSES) -> PoseDetector:
    """MediaPipe Pose Landmarker (modelo `.task` aparte). Solo guarda hombros y muñecas."""
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision

    options = vision.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.IMAGE,
        num_poses=num_poses,
    )
    landmarker = vision.PoseLandmarker.create_from_options(options)

    def detect(frame_rgb) -> list[Pose]:
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        result = landmarker.detect(image)
        return [
            {
                i: Point(lm[i].x, lm[i].y, lm[i].visibility or 0.0)
                for i in (LEFT_SHOULDER, RIGHT_SHOULDER, 15, 16)
            }
            for lm in result.pose_landmarks
        ]

    return detect


def main(argv: list[str] | None = None) -> None:
    from sources.manifest import ManifestError, require_ready

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--fps", type=float, default=SAMPLE_FPS)
    args = parser.parse_args(argv)
    load_dotenv()

    data_dir = Path(os.environ.get("DATA_DIR") or "data")
    try:
        require_ready(args.video, args.manifest or data_dir / "manifiesto.csv")
    except ManifestError as exc:
        raise SystemExit(str(exc)) from exc
    model = args.model or (Path(os.environ["POSE_MODEL"]) if os.environ.get("POSE_MODEL") else None)
    if model is None or not model.is_file():
        raise SystemExit("falta el modelo de pose: usa --model o POSE_MODEL en el .env (ver docs)")

    results = analyze_frames(iter_video_frames(args.video, args.fps), mediapipe_detector(model))
    out = data_dir / "processed" / args.video.stem / "video.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summarize(results), indent=2, ensure_ascii=False), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
