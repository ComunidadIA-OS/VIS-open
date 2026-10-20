"""Vídeo: personas visibles, seguimiento, tiempo en pantalla y manos levantadas. PROTOTIPO.

Baseline de la charla de visión (detectar → seguir → medir), SIN cara y SIN identificar a nadie:
1. Cada fotograma muestreado (2 por segundo): MediaPipe Pose Landmarker da los puntos del cuerpo
   de cada persona visible; de ahí salen su caja y las manos levantadas (`pipeline.gestures`).
2. Un seguimiento propio por solapamiento de cajas (tracking por detección) da a cada persona
   visible un número de pista anónimo.
3. Medidas por pista: tiempo en pantalla, tamaño medio y centralidad.
4. Género: NUNCA por la cara. Solo si el audio lo dice: cuando en el plano hay una única persona
   (primer plano) y la voz que habla tiene género por pistas del lenguaje, esa pista recibe el
   voto. Sin votos suficientes: `desconocido`.

Solo se escriben números; no se guardan imágenes. Límites: estimación de lo que ve la cámara (no de
quién hay en la sala); en planos amplios se cuenta de menos; el voto por audio supone que el
primer plano muestra a quien habla; cuando la cámara cambia de plano las zonas y las pistas no
son comparables.

Uso: python -m pipeline.video data/raw/V001.mp4 [--model ruta/pose_landmarker.task]
(el modelo también puede venir de POSE_MODEL en el `.env`; no se incluye en el repositorio).
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median

from pipeline.envfile import load_dotenv
from pipeline.gestures import LEFT_SHOULDER, RIGHT_SHOULDER, Point, Pose, raised_hands

ZONES = 4  # franjas horizontales de la imagen
SAMPLE_FPS = 2.0
NUM_POSES = 30  # máximo de personas por fotograma que pide a MediaPipe
IOU_MIN = 0.3  # solapamiento mínimo para seguir a la misma persona
MAX_LOST = 2  # fotogramas que una pista puede perderse y retomarse
MIN_VOTES, MIN_AGREEMENT = 3, 0.7  # para asignar género por audio a una pista
Box = tuple[float, float, float, float]  # x1, y1, x2, y2 normalizados 0..1


@dataclass(frozen=True)
class Person:
    pose: Pose
    box: Box


@dataclass(frozen=True)
class FrameResult:
    t_s: float
    boxes: list[Box]
    raised: list[tuple[str, str]] = field(default_factory=list)  # (zona, lado)

    @property
    def n_people(self) -> int:
        return len(self.boxes)


PersonDetector = Callable[[object], Sequence[Person]]  # fotograma RGB -> personas


def zone_of(pose: Pose, zones: int = ZONES) -> str:
    """Zona horizontal (Z1 izquierda … Zn derecha) según el punto medio de los hombros."""
    xs = [pose[i].x for i in (LEFT_SHOULDER, RIGHT_SHOULDER) if i in pose]
    x = sum(xs) / len(xs) if xs else 0.5
    return f"Z{min(zones, max(1, int(x * zones) + 1))}"


def analyze_frames(
    frames: Iterable[tuple[float, object]], detect: PersonDetector, **kw
) -> list[FrameResult]:
    """Aplica `detect` a cada (t_s, fotograma) y reúne cajas y manos levantadas."""
    out = []
    for t_s, frame in frames:
        people = list(detect(frame))
        raised = [
            (zone_of(p.pose), side) for p in people for side in sorted(raised_hands(p.pose, **kw))
        ]
        out.append(FrameResult(round(t_s, 3), [p.box for p in people], raised))
    return out


def iou(a: Box, b: Box) -> float:
    w = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    h = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = w * h
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def track_boxes(results: Sequence[FrameResult]) -> list[list[int]]:
    """Número de pista (anónimo) para cada caja de cada fotograma, por solapamiento (IoU).

    Tracking por detección, voraz: empareja primero los solapamientos mayores; una pista puede
    perderse hasta `MAX_LOST` fotogramas. Una persona que sale y vuelve a entrar puede recibir
    otra pista (límite conocido).
    """
    last: dict[int, tuple[Box, int]] = {}  # pista -> (última caja, último fotograma)
    next_id = 1
    ids: list[list[int]] = []
    for f, r in enumerate(results):
        active = {t: v for t, v in last.items() if f - v[1] <= MAX_LOST + 1}
        pairs = sorted(
            (
                (iou(box, tb), i, t)
                for i, box in enumerate(r.boxes)
                for t, (tb, _) in active.items()
            ),
            reverse=True,
        )
        assigned: dict[int, int] = {}
        used: set[int] = set()
        for score, i, t in pairs:
            if score < IOU_MIN:
                break
            if i not in assigned and t not in used:
                assigned[i] = t
                used.add(t)
        row = []
        for i, box in enumerate(r.boxes):
            if i not in assigned:
                assigned[i] = next_id
                next_id += 1
            last[assigned[i]] = (box, f)
            row.append(assigned[i])
        ids.append(row)
    return ids


def assign_genders(
    results: Sequence[FrameResult],
    ids: Sequence[Sequence[int]],
    voice_gender_at: Callable[[float], str | None],
) -> tuple[dict[int, str], dict[int, Counter]]:
    """Género por pista a partir del AUDIO (nunca de la cara): voto cuando hay una sola persona
    en plano y la voz que habla tiene género conocido."""
    votes: dict[int, Counter] = {}
    for r, row in zip(results, ids, strict=True):
        if len(row) == 1 and (g := voice_gender_at(r.t_s)) in ("mujer", "hombre"):
            votes.setdefault(row[0], Counter())[g] += 1
    genders = {}
    for track, c in votes.items():
        top, n = c.most_common(1)[0]
        total = sum(c.values())
        ok = total >= MIN_VOTES and n / total >= MIN_AGREEMENT
        genders[track] = top if ok else "desconocido"
    return genders, votes


def voice_gender_lookup(timeline) -> Callable[[float], str | None]:
    """Género (por pistas del lenguaje) de la voz que habla en cada instante, o None."""
    gender = {s.speaker_id: s.gender.value for s in timeline.speakers}
    spans = [
        (e.start_s, e.end_s, gender.get(e.speaker_id))
        for e in timeline.events
        if e.type.value == "speech" and e.speaker_id
    ]

    def at(t: float) -> str | None:
        return next((g for a, b, g in spans if a <= t <= b), None)

    return at


def _raise_intervals(results: Sequence[FrameResult], step: float, min_raise_s: float) -> dict:
    zones: dict[str, list[tuple[float, float]]] = {}
    open_runs: dict[tuple[str, str], list[float]] = {}

    def close(key, start, end):
        if end - start + step >= min_raise_s:
            zones.setdefault(key[0], []).append((start, end + step))

    for r in results:
        now = set(r.raised)
        for key in list(open_runs):
            if key not in now:
                close(key, *open_runs.pop(key))
        for key in now:
            open_runs.setdefault(key, [r.t_s, r.t_s])[1] = r.t_s
    for key, (start, end) in open_runs.items():
        close(key, start, end)
    return zones


def summarize(
    results: Sequence[FrameResult],
    min_raise_s: float = 1.0,
    voice_gender_at: Callable[[float], str | None] | None = None,
) -> dict:
    """Cifras del vídeo: personas visibles, tiempo en pantalla por pista y manos levantadas."""
    if not results:
        return {"n_fotogramas": 0}
    counts = [r.n_people for r in results]
    gaps = [b.t_s - a.t_s for a, b in zip(results, results[1:], strict=False)]
    step = median(gaps) if gaps else 0
    ids = track_boxes(results)
    genders, votes = assign_genders(results, ids, voice_gender_at or (lambda t: None))

    per_track: dict[int, dict] = {}
    for r, row in zip(results, ids, strict=True):
        for box, t in zip(r.boxes, row, strict=True):
            d = per_track.setdefault(t, {"frames": 0, "area": 0.0, "central": 0.0})
            d["frames"] += 1
            d["area"] += (box[2] - box[0]) * (box[3] - box[1])
            d["central"] += 1 - 2 * abs((box[0] + box[2]) / 2 - 0.5)
    tracks = [
        {
            "pista": t,
            "tiempo_en_pantalla_s": round(d["frames"] * step, 1),
            "tamano_medio": round(d["area"] / d["frames"], 3),
            "centralidad_media": round(d["central"] / d["frames"], 3),
            "genero_por_audio": genders.get(t, "desconocido"),
            "votos_audio": dict(votes.get(t, {})),
        }
        for t, d in sorted(per_track.items())
    ]
    by_gender: dict[str, float] = {"mujer": 0.0, "hombre": 0.0, "desconocido": 0.0}
    for t in tracks:
        by_gender[t["genero_por_audio"]] += t["tiempo_en_pantalla_s"]
    total = sum(by_gender.values())
    zones = _raise_intervals(results, step, min_raise_s)
    return {
        "aviso": (
            "Estimación de lo que ve la cámara, no de quién hay en la sala; sin caras ni "
            "identificación; el género sale solo del audio; en planos amplios se cuenta de menos."
        ),
        "n_fotogramas": len(results),
        "personas_visibles_max": max(counts),
        "personas_visibles_mediana": float(median(counts)),
        "fotogramas_sin_personas_%": round(100 * counts.count(0) / len(counts), 1),
        "personas_por_fotograma": [[r.t_s, r.n_people] for r in results],
        "pistas": tracks,
        "tiempo_en_pantalla_por_genero_s": {k: round(v, 1) for k, v in by_gender.items()},
        "tiempo_en_pantalla_por_genero_%": {
            k: round(100 * v / total, 1) if total else 0.0 for k, v in by_gender.items()
        },
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


def mediapipe_detector(model_path: Path, num_poses: int = NUM_POSES) -> PersonDetector:
    """MediaPipe Pose Landmarker (modelo `.task` aparte). Guarda hombros, muñecas y la caja."""
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision

    options = vision.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.IMAGE,
        num_poses=num_poses,
    )
    landmarker = vision.PoseLandmarker.create_from_options(options)

    def clamp(v: float) -> float:
        return min(1.0, max(0.0, v))

    def detect(frame_rgb) -> list[Person]:
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        people = []
        for lm in landmarker.detect(image).pose_landmarks:
            seen = [p for p in lm if (p.visibility or 0.0) >= 0.3]
            if not seen:
                continue
            box = (
                clamp(min(p.x for p in seen)),
                clamp(min(p.y for p in seen)),
                clamp(max(p.x for p in seen)),
                clamp(max(p.y for p in seen)),
            )
            pose = {
                i: Point(lm[i].x, lm[i].y, lm[i].visibility or 0.0)
                for i in (LEFT_SHOULDER, RIGHT_SHOULDER, 15, 16)
            }
            people.append(Person(pose, box))
        return people

    return detect


def main(argv: list[str] | None = None) -> None:
    from contracts import AnalysisTimeline
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
    env_model = os.environ.get("POSE_MODEL")
    model = args.model or (Path(env_model) if env_model else None)
    if model is None or not model.is_file():
        raise SystemExit("falta el modelo de pose: usa --model o POSE_MODEL en el .env (ver docs)")

    out_dir = data_dir / "processed" / args.video.stem
    voice = None
    if (out_dir / "timeline.json").is_file():  # género por audio, si la sesión ya está analizada
        text = (out_dir / "timeline.json").read_text("utf-8")
        voice = voice_gender_lookup(AnalysisTimeline.model_validate_json(text))
    results = analyze_frames(iter_video_frames(args.video, args.fps), mediapipe_detector(model))
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "video.json"
    summary = summarize(results, voice_gender_at=voice)
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
