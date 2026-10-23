"""Analiza una sesión de principio a fin, en la máquina donde se lanza (OVH o local).

Uso:
  python -m pipeline.sesion V008                      # el vídeo ya está en data/raw/V008.mp4
  python -m pipeline.sesion V008 --hls-url URL_MASTER.m3u8   # lo descarga (audio original)
  python -m pipeline.sesion V008 --video-url URL [--audio-url URL]   # o con las pistas sueltas
  python -m pipeline.sesion --buscar                  # plenos nuevos publicados: los descarga
  python -m pipeline.sesion --nuevos                  # vídeos de data/raw sin fila: la escribe
  python -m pipeline.sesion --pendientes              # todas las del manifiesto sin resultados
  python -m pipeline.sesion V008 --congreso-url URL_DE_LA_SESION --set tramo_inicio=00:06:13
      # descarga la emisión (sale de esa URL) y escribe la fila del manifiesto

Pasos: (0) descarga la emisión con ffmpeg si se da la URL (.m3u8); (1) audio, voces,
seudonimización y género (`pipeline.run`); (2) bloques de pregunta (`decision.roles`);
(3) M09 y M06 (`metrics.m09`, con Qwen si hay LLM_API_KEY, si no con reglas); (4) vídeo con
MediaPipe (`pipeline.video`) si hay POSE_MODEL. El panel recoge los resultados solo.

La fila del manifiesto la valida una persona: `sources.congreso` la deja con
`licencia_verificada=pendiente` y no se analiza hasta que alguien la revise y ponga `si`.
Los tokens no se leen de ningún fichero: vienen del entorno del terminal (`read -s`).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

from pipeline.envfile import load_dotenv
from sources.congreso import parse_session_url
from sources.manifest import ManifestError, read_manifest, require_ready, sha256_file


def _run(*args: str) -> float:
    """Ejecuta un paso (`python -m ...`) y devuelve cuántos segundos ha tardado."""
    print("→", " ".join(args), flush=True)
    start = time.monotonic()
    subprocess.run([sys.executable, "-m", *args], check=True)
    return round(time.monotonic() - start, 1)


STREAMING = "https://streaming.congreso.es:8443/vod/ondemand/video"
PLENO = "400"


def master_urls(congreso_url: str) -> list[str]:
    """Posibles master playlists de la sesión entera, a partir de la URL de su página.

    Patrón de las páginas (consultadas el 23 oct 2026): leg15/400/15_000400_202/cortes/
    smil:15_000400_202.smil/manifest.m3u8 (2026, con audio original aparte) o
    mp4:14_000400_207.mp4/manifest.m3u8 (2018, 2022).
    Legislatura, órgano con 6 cifras, sesión con 3.
    """
    s = parse_session_url(congreso_url)
    return stream_urls(s.legislatura, s.cod_organo, s.cod_sesion)


def session_id(congreso_url: str) -> str:
    """Nombre de una sesión nueva: «203_pleno_2026» (comisiones: «45_comision_2026»)."""
    s = parse_session_url(congreso_url)
    year = s.event_date[:4] or str(date.today().year)
    return f"{int(s.cod_sesion)}_{'pleno' if s.cod_organo == PLENO else 'comision'}_{year}"


def stream_urls(legislatura: str, organo: str, sesion: str | int) -> list[str]:
    sid = f"{legislatura}_{int(organo):06d}_{int(sesion):03d}"
    base = f"{STREAMING}/leg{legislatura}/{organo}/{sid}/cortes"
    return [f"{base}/smil:{sid}.smil/manifest.m3u8", f"{base}/mp4:{sid}.mp4/manifest.m3u8"]


def find_master(candidates: list[str]) -> tuple[str, str] | None:
    """(url, texto) de la primera master playlist que responde."""
    for url in candidates:
        master = _fetch(url)
        if master.startswith("#EXTM3U"):
            return url, master
    return None


def last_plenary(data_dir: Path) -> tuple[str, int] | None:
    """(legislatura, nº de sesión) del último pleno del manifiesto."""
    from sources.manifest import read_manifest as _read

    found = []
    for row in _read(data_dir / "manifiesto.csv").values():
        try:
            s = parse_session_url(row.get("url_origen") or "")
        except ValueError:
            continue
        if s.cod_organo == PLENO:
            found.append((int(s.legislatura), int(s.cod_sesion)))
    return (str(max(found)[0]), max(found)[1]) if found else None


def new_plenaries(data_dir: Path, look_ahead: int = 5) -> list[tuple[int, str, str]]:
    """Plenos publicados después del último del manifiesto: (nº de sesión, url, master).

    Para en el primer número que aún no existe. Solo plenos: las comisiones tienen muchos
    códigos de órgano y se añaden con su URL (--congreso-url).
    """
    last = last_plenary(data_dir)
    if last is None:
        return []
    leg, n = last
    out = []
    for ses in range(n + 1, n + 1 + look_ahead):
        hit = find_master(stream_urls(leg, PLENO, ses))
        if hit is None:
            break
        out.append((ses, *hit))
    return out


def _fetch(url: str) -> str:
    # certificado del servidor no verificable (igual que con curl -k al descargar a mano)
    r = subprocess.run(["curl", "-fsSk", "-m", "30", url], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


class InterpretationOnly(ValueError):
    """La emisión tiene varias pistas de audio y ninguna es la original."""


def _attrs(line: str) -> dict[str, str]:
    return {k: v.strip('"') for k, v in re.findall(r'([A-Z0-9-]+)=("[^"]*"|[^,]*)', line)}


def _plain(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def pick_tracks(master: str, base_url: str) -> tuple[str, str | None]:
    """(vídeo, audio) de una master playlist HLS: el vídeo de más calidad y SOLO el audio original.

    El canal «Castellano» es la interpretación simultánea y no se puede usar (condiciones del
    Congreso): si hay pistas de audio aparte y ninguna se llama «original», se para.
    """
    lines = master.splitlines()
    audios = [_attrs(x) for x in lines if x.startswith("#EXT-X-MEDIA:") and "TYPE=AUDIO" in x]
    variants = [
        (int(_attrs(x).get("BANDWIDTH") or 0), lines[i + 1].strip())
        for i, x in enumerate(lines[:-1])
        if x.startswith("#EXT-X-STREAM-INF:")
    ]
    if not variants:
        raise ValueError("no es una master playlist HLS (no hay #EXT-X-STREAM-INF)")
    video = urljoin(base_url, max(variants)[1])
    separate = [a for a in audios if a.get("URI")]
    if not separate:
        return video, None  # un solo audio, dentro del vídeo
    original = [a for a in separate if "original" in _plain(a.get("NAME", ""))]
    if not original:
        names = ", ".join(a.get("NAME", "?") for a in separate)
        raise InterpretationOnly(f"ninguna pista de audio es la original ({names}): no se descarga")
    return video, urljoin(base_url, original[0]["URI"])


def download(video: Path, video_url: str, audio_url: str | None = None) -> None:
    """Emisión HLS → mp4 sin recodificar. `audio_url`: pista aparte (p. ej. «Versión original»)."""
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", video_url]
    if audio_url:  # el canal «Castellano» es la interpretación: se usa el audio original aparte
        cmd += ["-i", audio_url, "-map", "0:v:0", "-map", "1:a:0"]
    video.parent.mkdir(parents=True, exist_ok=True)
    print("→ descargando", video, flush=True)
    # a un .part: el nombre definitivo solo existe con el fichero completo (nadie lee uno a medias)
    part = partial(video)
    subprocess.run([*cmd, "-c", "copy", "-f", "mp4", str(part)], check=True)
    part.replace(video)
    print(f"sha256 de {video.name}: {sha256_file(video)}")


def partial(video: Path) -> Path:
    return video.with_name(video.name + ".part")


def pending(data_dir: Path) -> list[str]:
    """Sesiones con fila en el manifiesto y vídeo en data/raw, pero sin timeline todavía."""
    rows = read_manifest(data_dir / "manifiesto.csv")
    return [
        vid
        for vid in rows
        if (data_dir / "raw" / f"{vid}.mp4").is_file()
        and not (data_dir / "processed" / vid / "timeline.json").is_file()
    ]


def new_videos(data_dir: Path) -> list[Path]:
    """Vídeos de data/raw que aún no tienen fila en el manifiesto."""
    manifest = data_dir / "manifiesto.csv"
    known = read_manifest(manifest) if manifest.is_file() else {}
    return sorted(v for v in (data_dir / "raw").glob("*.mp4") if v.stem not in known)


def session_cost(seconds: dict[str, float], m09: dict | None, env=os.environ) -> dict:
    """Coste real de una sesión, de la descarga al último análisis, con los precios del .env.

    La máquina con GPU se paga mientras está encendida, también al descargar y en los pasos de
    CPU: por eso se cuenta el tiempo total. GPU_PRICE_EUR_H = precio por hora de una GPU;
    GPU_COUNT = GPU que se facturan en esa máquina (aunque el programa use una).
    """
    total_s = round(sum(v for v in seconds.values() if v), 1)
    use = (m09 or {}).get("consumo") or {}
    out = {
        "segundos_totales": total_s,
        "qwen_llamadas": use.get("llamadas", 0),
        "qwen_tokens_in": use.get("tokens_in", 0),
        "qwen_tokens_out": use.get("tokens_out", 0),
    }
    try:
        gpu = float(env["GPU_PRICE_EUR_H"]) * int(env.get("GPU_COUNT") or 1)
        out["maquina_eur"] = round(total_s / 3600 * gpu, 4)
    except (KeyError, ValueError):
        out["maquina_eur"] = None
    try:
        qwen = (
            out["qwen_tokens_in"] * float(env["LLM_PRICE_IN_PER_MTOK"])
            + out["qwen_tokens_out"] * float(env["LLM_PRICE_OUT_PER_MTOK"])
        ) / 1e6
        out["qwen_eur"] = round(qwen, 6)
    except (KeyError, ValueError):
        out["qwen_eur"] = None if out["qwen_tokens_in"] else 0.0
    parts = [out["maquina_eur"], out["qwen_eur"]]
    out["total_eur"] = round(sum(parts), 4) if None not in parts else None
    out["precios"] = {
        k: env.get(k)
        for k in ("GPU_PRICE_EUR_H", "GPU_COUNT", "LLM_PRICE_IN_PER_MTOK", "LLM_PRICE_OUT_PER_MTOK",
                  "LLM_PRICE_DATE")
    }  # fmt: skip
    if out["total_eur"] is None:
        out["aviso"] = "faltan precios en el .env (GPU_PRICE_EUR_H, LLM_PRICE_*): solo tiempos"
    return out


def analyze_session(video_id: str, data_dir: Path) -> None:
    video = data_dir / "raw" / f"{video_id}.mp4"
    require_ready(video, data_dir / "manifiesto.csv")  # antes de gastar GPU
    timeline = data_dir / "processed" / video_id / "timeline.json"
    times_file = timeline.with_name("tiempos.json")
    seconds = json.loads(times_file.read_text("utf-8")) if times_file.is_file() else {}
    seconds["audio_y_voces"] = _run("pipeline.run", str(video))
    seconds["bloques_pregunta"] = _run("decision.roles", str(timeline))
    engine = "llm" if os.environ.get("LLM_API_KEY") else "rules"
    print(f"M09/M06 con el motor «{engine}»", flush=True)
    seconds[f"m09_{engine}"] = _run("metrics.m09", str(timeline), "--engine", engine)
    model = os.environ.get("POSE_MODEL")
    if model and Path(model).is_file():
        seconds["video"] = _run("pipeline.video", str(video), "--model", model)
    else:
        print("sin POSE_MODEL: no se analiza el vídeo (el resto ya está en el panel)")
    # tiempo real de cada paso, para el documento de costes (GPU encendida = se factura)
    times_file.parent.mkdir(parents=True, exist_ok=True)
    times_file.write_text(json.dumps(seconds, indent=2), encoding="utf-8")
    print("tiempos (s):", seconds)
    m09_file = timeline.with_name("m09.json")
    m09 = json.loads(m09_file.read_text("utf-8")) if m09_file.is_file() else None
    cost = session_cost(seconds, m09)
    timeline.with_name("coste.json").write_text(json.dumps(cost, indent=2), encoding="utf-8")
    print("coste:", cost)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("video_id", nargs="?")
    ap.add_argument("--pendientes", action="store_true")
    ap.add_argument("--buscar", action="store_true", help="descarga los plenos nuevos publicados")
    ap.add_argument("--nuevos", action="store_true", help="escribe la fila de los vídeos nuevos")
    ap.add_argument("--hls-url", help="master playlist (.m3u8): elige vídeo y audio original")
    ap.add_argument("--video-url")
    ap.add_argument("--audio-url")
    ap.add_argument("--congreso-url", help="página de la sesión: escribe su fila del manifiesto")
    ap.add_argument("--set", action="append", default=[], metavar="CAMPO=VALOR")
    args = ap.parse_args(argv)
    load_dotenv()
    data_dir = Path(os.environ.get("DATA_DIR") or "data")
    sets = [x for s in args.set for x in ("--set", s)]
    if args.buscar:  # descarga y escribe la fila; el análisis espera a que una persona la valide
        found = new_plenaries(data_dir)
        for ses, url, master in found:
            try:
                video_url, audio_url = pick_tracks(master, url)
            except ValueError as exc:
                print(f"pleno {ses}: {exc}")
                continue
            vid = f"{ses}_pleno_{date.today().year}"  # se publica días después: el año en curso
            raw = data_dir / "raw" / f"{vid}.mp4"
            manifest = data_dir / "manifiesto.csv"
            if partial(raw).exists() or (manifest.is_file() and vid in read_manifest(manifest)):
                print(f"{vid}: ya descargado o descargándose; no se repite")
                continue
            if not raw.is_file():
                start = time.monotonic()
                download(raw, video_url, audio_url)
                times = data_dir / "processed" / vid / "tiempos.json"
                times.parent.mkdir(parents=True, exist_ok=True)
                spent = round(time.monotonic() - start, 1)
                times.write_text(json.dumps({"deteccion_y_descarga": spent}), encoding="utf-8")
            _run(
                "sources.congreso", "--file", str(raw), "--set", "tipo_sesion=pleno",
                "--set", f"titulo=Pleno, sesión {ses}", "--set", f"notas=emisión: {url}",
                "--set", f"fecha_descarga={date.today().isoformat()}",
                "--set", "descargado_por=pipeline.sesion (automático)",
            )  # fmt: skip
        print(f"{len(found)} plenos nuevos; valida sus filas y lanza --pendientes")
        return
    if args.nuevos:  # solo escribe filas: el análisis espera a que una persona las valide
        videos = new_videos(data_dir)
        for video in videos:
            _run("sources.congreso", "--file", str(video), *sets)
        print(f"{len(videos)} filas nuevas; complétalas y valídalas antes de --pendientes")
        return
    if args.congreso_url and not args.video_id:
        args.video_id = session_id(args.congreso_url)
        print("nombre:", args.video_id)
    if args.pendientes == bool(args.video_id):
        ap.error("indica una sesión (V008), --pendientes o --nuevos")
    raw = data_dir / "raw" / f"{args.video_id}.mp4" if args.video_id else None
    candidates = [args.hls_url] if args.hls_url else []
    if args.congreso_url and not (args.hls_url or args.video_url) and not raw.is_file():
        candidates = master_urls(args.congreso_url)  # la emisión sale de la URL de la sesión
    for url in candidates:
        master = _fetch(url)
        if master.startswith("#EXTM3U"):
            print("emisión:", url)
            try:
                args.video_url, args.audio_url = pick_tracks(master, url)
            except ValueError as exc:
                raise SystemExit(str(exc)) from exc
            break
    else:
        if candidates:
            raise SystemExit("no se encuentra la emisión: pásala con --hls-url")
    if args.video_url:
        download(data_dir / "raw" / f"{args.video_id}.mp4", args.video_url, args.audio_url)
    manifest = data_dir / "manifiesto.csv"
    has_row = manifest.is_file() and args.video_id in read_manifest(manifest)
    if args.congreso_url and has_row:
        print(f"{args.video_id} ya tiene fila en el manifiesto: no se escribe otra")
    elif args.congreso_url:
        video = data_dir / "raw" / f"{args.video_id}.mp4"
        _run("sources.congreso", "--url", args.congreso_url, "--file", str(video), *sets)
    try:
        ids = pending(data_dir) if args.pendientes else [args.video_id]
    except ManifestError as exc:
        raise SystemExit(str(exc)) from exc
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
