"""Analiza una sesión de principio a fin, en la máquina donde se lanza (OVH o local).

Uso:
  python -m pipeline.sesion V008                      # el vídeo ya está en data/raw/V008.mp4
  python -m pipeline.sesion V008 --video-url URL [--audio-url URL]   # lo descarga antes
  python -m pipeline.sesion --pendientes              # todas las del manifiesto sin resultados

Pasos: (0) descarga la emisión con ffmpeg si se da la URL (.m3u8); (1) audio, voces,
seudonimización y género (`pipeline.run`); (2) bloques de pregunta (`decision.roles`);
(3) M09 y M06 (`metrics.m09`, con Qwen si hay LLM_API_KEY, si no con reglas); (4) vídeo con
MediaPipe (`pipeline.video`) si hay POSE_MODEL. El panel recoge los resultados solo.

La fila del manifiesto la valida una persona antes: sin ella (o con otro sha256) no se analiza.
Tras descargar se imprime el sha256 para anotarlo en la fila. Los tokens no se leen de ningún
fichero: vienen del entorno del terminal (`read -s`).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from pipeline.envfile import load_dotenv
from sources.manifest import ManifestError, read_manifest, require_ready, sha256_file


def _run(*args: str) -> None:
    print("→", " ".join(args), flush=True)
    subprocess.run([sys.executable, "-m", *args], check=True)


def download(video: Path, video_url: str, audio_url: str | None = None) -> None:
    """Emisión HLS → mp4 sin recodificar. `audio_url`: pista aparte (p. ej. «Versión original»)."""
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", video_url]
    if audio_url:  # el canal «Castellano» es la interpretación: se usa el audio original aparte
        cmd += ["-i", audio_url, "-map", "0:v:0", "-map", "1:a:0"]
    video.parent.mkdir(parents=True, exist_ok=True)
    print("→ descargando", video, flush=True)
    subprocess.run([*cmd, "-c", "copy", str(video)], check=True)
    print(f"sha256 de {video.name}: {sha256_file(video)} (anótalo en la fila del manifiesto)")


def pending(data_dir: Path) -> list[str]:
    """Sesiones con fila en el manifiesto y vídeo en data/raw, pero sin timeline todavía."""
    rows = read_manifest(data_dir / "manifiesto.csv")
    return [
        vid
        for vid in rows
        if (data_dir / "raw" / f"{vid}.mp4").is_file()
        and not (data_dir / "processed" / vid / "timeline.json").is_file()
    ]


def analyze_session(video_id: str, data_dir: Path) -> None:
    video = data_dir / "raw" / f"{video_id}.mp4"
    require_ready(video, data_dir / "manifiesto.csv")  # antes de gastar GPU
    timeline = data_dir / "processed" / video_id / "timeline.json"
    _run("pipeline.run", str(video))
    _run("decision.roles", str(timeline))
    engine = "llm" if os.environ.get("LLM_API_KEY") else "rules"
    print(f"M09/M06 con el motor «{engine}»", flush=True)
    _run("metrics.m09", str(timeline), "--engine", engine)
    model = os.environ.get("POSE_MODEL")
    if model and Path(model).is_file():
        _run("pipeline.video", str(video), "--model", model)
    else:
        print("sin POSE_MODEL: no se analiza el vídeo (el resto ya está en el panel)")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("video_id", nargs="?")
    ap.add_argument("--pendientes", action="store_true")
    ap.add_argument("--video-url")
    ap.add_argument("--audio-url")
    args = ap.parse_args(argv)
    load_dotenv()
    data_dir = Path(os.environ.get("DATA_DIR") or "data")
    if args.pendientes == bool(args.video_id):
        ap.error("indica una sesión (V008) o --pendientes, no las dos")
    if args.video_url:
        download(data_dir / "raw" / f"{args.video_id}.mp4", args.video_url, args.audio_url)
    ids = pending(data_dir) if args.pendientes else [args.video_id]
    if not ids:
        print("no hay sesiones pendientes")
    for vid in ids:
        try:
            analyze_session(vid, data_dir)
        except ManifestError as exc:
            print(f"{vid}: {exc}")  # la sigue otra; esta espera a que se complete su fila
        except subprocess.CalledProcessError as exc:
            raise SystemExit(
                f"{vid}: falló el paso {exc.cmd[2]} (código {exc.returncode})"
            ) from exc


if __name__ == "__main__":
    main()
