"""Capa de datos del panel: lee los ficheros del análisis y calcula las cifras con `metrics/`.

Sin Streamlit aquí, para poder probarla. Nunca muestra nombres: cada voz es «Persona N».
Si falta una métrica (M09, M14), se informa como «no disponible todavía».
"""

from __future__ import annotations

import csv
import io
import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from contracts import (
    AnalysisTimeline,
    AnnotatorConfidence,
    EventType,
    GenderSource,
    GenderValue,
    ReviewRow,
    read_rows,
    write_rows,
)
from decision.pseudonymize import speaker_codes
from metrics import MetricResult, run_metric, timeline_to_frame

CARD_METRICS = ["M01", "M02", "M03", "M04", "M13"]
PENDING_METRICS = {
    "M14": "Peticiones de palabra con la mano (vídeo)",
    "M09": "Preguntas recibidas (IA)",
}
METHOD_NOTICE = (
    "El género asignado por IA solo se hace por pistas del lenguaje de la sesión, nunca por la "
    "cara ni la voz. "
    "Los resultados son orientativos y requieren revisión humana."
)
SOURCE_NOTICE = "Fuente: Congreso de los Diputados, vídeo sin alterar."
SYNTHETIC_DIR = Path(__file__).parent.parent / "evaluation" / "synthetic" / "muestras"


@dataclass
class Session:
    session_id: str
    timeline: AnalysisTimeline
    source: dict | None = None
    summary: dict | None = None
    video: dict | None = None
    confirmed: dict[str, str] = field(default_factory=dict)  # voz → género de 2 anotadoras
    synthetic: bool = False
    metrics: dict[str, MetricResult] = field(default_factory=dict)


def _read_json(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def load_sessions(data_dir: Path | None = None) -> list[Session]:
    """Sesiones de `<data_dir>/processed/*/`; si no hay ninguna, las SINTÉTICAS del repositorio."""
    processed = Path(data_dir or "data") / "processed"
    sessions = []
    for folder in sorted(p for p in processed.glob("*") if (p / "timeline.json").is_file()):
        tl = AnalysisTimeline.model_validate_json((folder / "timeline.json").read_text("utf-8"))
        sessions.append(
            Session(
                folder.name,
                tl,
                _read_json(folder / "source.json"),
                _read_json(folder / "resumen.json"),
                video=_read_json(folder / "video.json"),
            )
        )
    if not sessions:
        for path in sorted(SYNTHETIC_DIR.glob("*.timeline.json")):
            tl = AnalysisTimeline.model_validate_json(path.read_text("utf-8"))
            sessions.append(Session(tl.video_id, tl, synthetic=True))
    for s in sessions:
        if not s.synthetic:
            s.confirmed = agreed_genders(processed / s.session_id)
            s.timeline = apply_confirmed(s.timeline, s.confirmed)
        frame = timeline_to_frame(s.timeline)
        s.metrics = {m: run_metric(m, frame) for m in CARD_METRICS}
    return sessions


ANNOTATORS = (1, 2)
KNOWN = {GenderValue.WOMAN.value, GenderValue.MAN.value}


def _review_file(folder: Path, n: int) -> Path:
    return folder / f"review_anotadora_{n}.csv"


def voices_to_review(folder: Path) -> list[ReviewRow]:
    """Voces que el análisis por lenguaje dejó sin género (`review_genero.csv`)."""
    path = folder / "review_genero.csv"
    return read_rows(ReviewRow, path) if path.is_file() else []


CONNECTION_ID = re.compile(r"^[A-Za-z0-9_-]{2,20}$")


def valid_connection_id(value: str) -> bool:
    """ID de conexión: un código corto sin espacios (nunca un nombre ni un correo)."""
    return bool(CONNECTION_ID.match(value or ""))


def save_review(
    folder: Path,
    n: int,
    speaker_id: str,
    gender: str,
    confidence: str,
    notes: str,
    connection_id: str,
) -> None:
    """Guarda la decisión de la anotadora `n` (con su ID de conexión) sobre una voz en su CSV."""
    if not valid_connection_id(connection_id):
        raise ValueError("ID de conexión no válido: 2 a 20 letras, números, - o _")
    path = _review_file(folder, n)
    rows = (
        read_rows(ReviewRow, path)
        if path.is_file()
        else [
            r.model_copy(update={"annotator_id": connection_id}) for r in voices_to_review(folder)
        ]
    )
    row = next((r for r in rows if r.speaker_id == speaker_id), None)
    if row is None:
        raise ValueError(f"voz desconocida: {speaker_id}")
    row.gender = GenderValue(gender)
    row.confidence = AnnotatorConfidence(confidence)
    row.notes = notes or None
    row.annotator_id = connection_id
    write_rows(rows, ReviewRow, path)


def make_clip(video: Path, start_s: float, stop_s: float, out_dir: Path, name: str) -> Path | None:
    """Corta de verdad el tramo [start, stop] a un MP4 pequeño (FFmpeg); None si no se puede.

    Así el reproductor solo tiene esos segundos (con `start_time`/`end_time` seguiría mostrando
    el vídeo entero). El recorte se guarda en `out_dir` (dentro de `data/`, fuera del repo).
    """
    out = Path(out_dir) / f"{name}_{int(start_s)}_{int(stop_s)}.mp4"
    if out.is_file():
        return out
    if shutil.which("ffmpeg") is None or stop_s <= start_s:
        return None
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start_s:.2f}", "-i", str(video),
        "-t", f"{stop_s - start_s:.2f}", "-vf", "scale=-2:360", "-c:v", "libx264",
        "-preset", "veryfast", "-crf", "28", "-c:a", "aac", "-b:a", "96k",
        "-movflags", "+faststart", str(out),
    ]  # fmt: skip
    done = subprocess.run(cmd, capture_output=True, timeout=120, check=False)  # noqa: S603
    if done.returncode != 0 or not out.is_file():
        out.unlink(missing_ok=True)
        return None
    return out


def fmt_time(seconds: float) -> str:
    m, sec = divmod(int(seconds), 60)
    return f"{m}:{sec:02d}"


def fmt_pct(value: float) -> str:
    return f"{value:.1f} %"


def show_interventions(rows: pd.DataFrame) -> pd.DataFrame:
    """Intervenciones para pantalla: inicio y duración en m:ss."""
    return pd.DataFrame(
        {
            "persona": rows["persona"],
            "inicio": [fmt_time(m * 60) for m in rows["inicio_min"]],
            "duración": [fmt_time(d) for d in rows["duracion_s"]],
            "género": rows["genero"],
            "texto": rows["texto"],
        }
    )


def show_voices(voices: pd.DataFrame) -> pd.DataFrame:
    """Voces para pantalla: tiempo de palabra en m:ss."""
    return pd.DataFrame(
        {
            "persona": voices["persona"],
            "género": voices["genero"],
            "origen": voices["origen"],
            "tiempo de palabra": [fmt_time(m * 60) for m in voices["minutos"]],
            "intervenciones": voices["intervenciones"],
        }
    )


def show_tracks(tracks: pd.DataFrame) -> pd.DataFrame:
    """Pistas de vídeo para pantalla: tiempo en m:ss, porcentaje con %, vacíos sin símbolo."""

    def num(x: float) -> str:
        return "" if pd.isna(x) else f"{x:.2f}"

    return pd.DataFrame(
        {
            "pista": tracks["pista"],
            "tiempo en pantalla": [fmt_time(m * 60) for m in tracks["minutos_en_pantalla"]],
            "% del tiempo": [fmt_pct(x) for x in tracks["porcentaje"]],
            "tamaño medio": [num(x) for x in tracks["tamano_medio"]],
            "centralidad": [num(x) for x in tracks["centralidad"]],
            "género (audio)": tracks["genero_por_audio"],
        }
    )


def voice_blocks(
    timeline: AnalysisTimeline, speaker_id: str, gap_s: float = 3.0, top: int = 3
) -> list[tuple[float, float]]:
    """Tramos seguidos de una voz (pausas de hasta `gap_s`), los `top` más largos, en orden."""
    events = sorted(
        (e for e in timeline.events if e.type == EventType.SPEECH and e.speaker_id == speaker_id),
        key=lambda e: e.start_s,
    )
    blocks: list[list[float]] = []
    for e in events:
        if blocks and e.start_s - blocks[-1][1] <= gap_s:
            blocks[-1][1] = e.end_s
        else:
            blocks.append([e.start_s, e.end_s])
    longest = sorted(blocks, key=lambda b: b[0] - b[1])[:top]
    return [(b[0], b[1]) for b in sorted(longest)]


def transcript_turns(session: Session, max_words: int = 60, gap_s: float = 3.0) -> list[dict]:
    """Transcripción seudonimizada en trozos legibles: inicio, persona (código), género y texto."""
    codes = speaker_codes(session.timeline)
    gender = {sp.speaker_id: sp.gender.value for sp in session.timeline.speakers}
    events = sorted(
        (e for e in session.timeline.events if e.type == EventType.SPEECH and e.text),
        key=lambda e: e.start_s,
    )
    turns: list[dict] = []
    last_end = 0.0
    for e in events:
        prev = turns[-1] if turns else None
        if (
            prev
            and prev["speaker_id"] == e.speaker_id
            and e.start_s - last_end <= gap_s
            and len(prev["texto"].split()) < max_words
        ):
            prev["texto"] += " " + e.text.strip()
        else:
            turns.append(
                {
                    "inicio_s": e.start_s,
                    "speaker_id": e.speaker_id,
                    "persona": codes.get(e.speaker_id, "sin atribuir"),
                    "genero": gender.get(e.speaker_id, "sin_atribuir"),
                    "texto": e.text.strip(),
                }
            )
        last_end = e.end_s
    return turns


def voice_transcripts(session: Session) -> dict[str, list[dict]]:
    """Transcripción seudonimizada agrupada por voz («Persona N»), en orden de aparición."""
    out: dict[str, list[dict]] = {}
    for t in transcript_turns(session):
        out.setdefault(t["persona"], []).append(t)
    return out


def transcript_csv(session: Session) -> str:
    """Transcripción completa en CSV (UTF-8): inicio, persona, género y texto."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["inicio_s", "inicio", "persona", "genero", "texto"])
    for t in transcript_turns(session):
        writer.writerow(
            [
                round(t["inicio_s"], 2),
                fmt_time(t["inicio_s"]),
                t["persona"],
                t["genero"],
                t["texto"],
            ]
        )
    return buf.getvalue()


SAMPLE_S = 9  # segundos de cada corte que se valida
MIN_CUT_S = 4.0  # un corte más corto que esto casi no se oye: se prefieren los largos


def annotator_answers(folder: Path, n: int) -> dict[str, str]:
    """Voz → género que la anotadora `n` ya ha puesto (vale para todos los cortes de esa voz)."""
    path = _review_file(folder, n)
    rows = read_rows(ReviewRow, path) if path.is_file() else []
    return {r.speaker_id: r.gender.value for r in rows if r.gender}


def cut_text(timeline: AnalysisTimeline, speaker_id: str, start_s: float, stop_s: float) -> str:
    """Lo que dice esa voz en el tramo (texto seudonimizado)."""
    events = sorted(
        (
            e
            for e in timeline.events
            if e.type == EventType.SPEECH
            and e.speaker_id == speaker_id
            and e.text
            and e.end_s > start_s
            and e.start_s < stop_s
        ),
        key=lambda e: e.start_s,
    )
    return " ".join(e.text.strip() for e in events)


def review_cuts(
    session: Session, speaker_ids: list[str], per_voice: int = 6
) -> list[dict[str, float | str]]:
    """Cortes para validar, uno detrás de otro (por orden en el vídeo), de las voces dadas."""
    cuts: list[dict[str, float | str]] = []
    for sid in speaker_ids:
        blocks = voice_blocks(session.timeline, sid, top=per_voice)
        long = [b for b in blocks if b[1] - b[0] >= MIN_CUT_S] or blocks[:1]
        for start, end in long:
            stop = min(end, start + SAMPLE_S)
            cuts.append(
                {
                    "speaker_id": sid,
                    "start": start,
                    "stop": stop,
                    "texto": cut_text(session.timeline, sid, start, stop),
                }
            )
    return sorted(cuts, key=lambda c: float(c["start"]))


LINE_CHARS = 42  # ancho de línea de subtítulo recomendado


def _vtt_time(seconds: float) -> str:
    ms = round(max(seconds, 0.0) * 1000)
    h, rest = divmod(ms, 3_600_000)
    m, rest = divmod(rest, 60_000)
    return f"{h:02d}:{m:02d}:{rest // 1000:02d}.{rest % 1000:03d}"


def _wrap_lines(text: str, width: int = LINE_CHARS) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        if current and len(current) + 1 + len(word) > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    return [*lines, current] if current else lines


def subtitles_vtt(session: Session, start_s: float = 0.0, end_s: float | None = None) -> str:
    """Subtítulos WebVTT de la transcripción (seudonimizada), con «Persona N:» al cambiar de voz.

    Con `start_s`/`end_s` solo el tramo, con los tiempos desplazados para un clip que empieza en 0.
    Son subtítulos automáticos (Whisper): pueden tener errores.
    """
    stop = float("inf") if end_s is None else end_s
    codes = speaker_codes(session.timeline)
    events = sorted(
        (
            e
            for e in session.timeline.events
            if e.type == EventType.SPEECH and e.text and e.end_s > start_s and e.start_s < stop
        ),
        key=lambda e: e.start_s,
    )
    cues = ["WEBVTT", ""]
    last_speaker = None
    for e in events:
        lines = _wrap_lines(e.text.strip())
        if e.speaker_id != last_speaker and e.speaker_id:
            lines = [f"{codes.get(e.speaker_id, e.speaker_id)}:", *lines]
        last_speaker = e.speaker_id
        groups = [lines[i : i + 2] for i in range(0, len(lines), 2)]  # 2 líneas por subtítulo
        begin, finish = max(e.start_s, start_s), min(e.end_s, stop)
        total = sum(len(" ".join(g)) for g in groups) or 1
        t = begin
        for group in groups:
            span = (finish - begin) * len(" ".join(group)) / total
            cues += [
                f"{_vtt_time(t - start_s)} --> {_vtt_time(t + span - start_s)}",
                *group,
                "",
            ]
            t += span
    return "\n".join(cues)


def agreed_genders(folder: Path) -> dict[str, str]:
    """Voz → género, solo si dos anotadoras con ID de conexión distinto pusieron el mismo."""
    answers: list[dict[str, tuple[str, str]]] = []
    for n in ANNOTATORS:
        path = _review_file(folder, n)
        rows = read_rows(ReviewRow, path) if path.is_file() else []
        answers.append(
            {r.speaker_id: (r.gender.value, r.annotator_id or "") for r in rows if r.gender}
        )
    first, second = answers
    return {
        k: g
        for k, (g, who) in first.items()
        if g in KNOWN and second.get(k, ("", ""))[0] == g and who and who != second[k][1]
    }


def apply_confirmed(timeline: AnalysisTimeline, confirmed: dict[str, str]) -> AnalysisTimeline:
    """Pone el género confirmado por dos anotadoras a las voces que seguían en `desconocido`."""
    speakers = [
        s.model_copy(
            update={
                "gender": GenderValue(confirmed[s.speaker_id]),
                "gender_source": GenderSource.PERCEIVED_BY_ANNOTATORS,
            }
        )
        if s.gender == GenderValue.UNKNOWN and s.speaker_id in confirmed
        else s
        for s in timeline.speakers
    ]
    return timeline.model_copy(update={"speakers": speakers})


def inconclusive_reason(session: Session) -> str:
    """Por qué hay métricas «no concluyentes» (vacío si todas lo son por otra cosa o ninguna)."""
    reasons = sorted(
        {
            r.reason.removeprefix("no concluyente: ")
            for r in session.metrics.values()
            if not r.conclusive and r.reason
        }
    )
    if not reasons:
        return ""
    return (
        f"Por qué «no concluyente»: {'; '.join(reasons)}. Hace falta una muestra mínima "
        "(umbral provisional, lo fija Ivette); se alcanza confirmando las voces en "
        "Human in the loop."
    )


def metric_card(result: MetricResult) -> dict:
    """Texto de una tarjeta: cifra o «no concluyente»; la muestra siempre se ve."""
    if not result.conclusive:
        return {"titulo": result.name, "valor": "no concluyente", "detalle": result.reason or ""}
    return {
        "titulo": result.name,
        "valor": f"{result.value:g}",
        "detalle": json.dumps(result.details, ensure_ascii=False),
    }


def gender_time_table(session: Session) -> pd.DataFrame:
    """Minutos y porcentaje por mujer / hombre / desconocido / sin_atribuir (M02)."""
    d = session.metrics["M02"].details
    if not d:
        from metrics import speech_time_by_gender

        t = speech_time_by_gender(timeline_to_frame(session.timeline))
        return t.assign(
            minutos=(t["seconds"] / 60).round(2), porcentaje=(100 * t["share"]).round(2)
        )[["gender", "minutos", "porcentaje"]]
    return pd.DataFrame(
        {
            "gender": list(d["minutos"]),
            "minutos": list(d["minutos"].values()),
            "porcentaje": list(d["porcentaje_sobre_total"].values()),
        }
    )


def interventions_table(session: Session) -> pd.DataFrame:
    """Una fila por evento de habla: persona (código), minuto, duración, género y evidencia."""
    tl = session.timeline
    codes = speaker_codes(tl)
    spk = {s.speaker_id: s for s in tl.speakers}
    rows = []
    for e in tl.events:
        if e.type != EventType.SPEECH:
            continue
        s = spk.get(e.speaker_id) if e.speaker_id else None
        ev = s.gender_evidence[0] if s and s.gender_evidence else None
        rows.append(
            {
                "persona": codes.get(e.speaker_id, "sin atribuir"),
                "inicio_min": round(e.start_s / 60, 2),
                "duracion_s": round(e.end_s - e.start_s, 1),
                "genero": s.gender.value if s else "sin_atribuir",
                "evidencia": f"[min {ev.minute}] {ev.method}: {ev.phrase}" if ev else "",
                "texto": e.text or "",
            }
        )
    return pd.DataFrame(
        rows, columns=["persona", "inicio_min", "duracion_s", "genero", "evidencia", "texto"]
    )


def voices_table(session: Session) -> pd.DataFrame:
    """Una fila por voz: género, de dónde sale, minutos de palabra, intervenciones y evidencia."""
    tl = session.timeline
    codes = speaker_codes(tl)
    speech = [e for e in tl.events if e.type == EventType.SPEECH and e.speaker_id]
    rows = []
    for sp in tl.speakers:
        mine = [e for e in speech if e.speaker_id == sp.speaker_id]
        ev = sp.gender_evidence[0] if sp.gender_evidence else None
        rows.append(
            {
                "persona": codes.get(sp.speaker_id, sp.speaker_id),
                "genero": sp.gender.value,
                "origen": sp.gender_source.value,
                "minutos": round(sum(e.end_s - e.start_s for e in mine) / 60, 2),
                "intervenciones": len(mine),
                "evidencia": f"{ev.method}: {ev.phrase}" if ev else "",
            }
        )
    return pd.DataFrame(
        rows,
        columns=["persona", "genero", "origen", "minutos", "intervenciones", "evidencia"],
    ).sort_values("minutos", ascending=False, ignore_index=True)


def timeline_strip(session: Session) -> pd.DataFrame:
    """Franja de la sesión: tramos coloreados por género (y manos levantadas, si las hay)."""
    f = timeline_to_frame(session.timeline)
    f = f[f["type"].isin(["speech", "hand_raise"])]
    return pd.DataFrame(
        {
            "inicio_min": f["start_s"] / 60,
            "fin_min": f["end_s"] / 60,
            "genero": f["gender"].where(f["type"] == "speech", "mano_levantada"),
        }
    )


def video_path(session: Session, data_dir: Path | None = None) -> Path | None:
    """Vídeo original de la sesión (`<data>/raw/<id>.mp4`), solo si está en este equipo."""
    path = Path(data_dir or "data") / "raw" / f"{session.session_id}.mp4"
    return path if path.is_file() else None


def video_tables(session: Session) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """(tiempo en pantalla por género, manos levantadas por zona) del módulo de vídeo, o None.

    Es lo que ve la cámara, no quién hay en la sala; el aviso del módulo debe mostrarse a su lado.
    """
    v = session.video
    if not v:
        return None
    screen = pd.DataFrame(
        {
            "genero": list(v["tiempo_en_pantalla_por_genero_s"]),
            "minutos": [round(x / 60, 2) for x in v["tiempo_en_pantalla_por_genero_s"].values()],
            "porcentaje": list(v["tiempo_en_pantalla_por_genero_%"].values()),
        }
    )
    hands = pd.DataFrame(
        {
            "zona": list(v["manos_levantadas_por_zona"]),
            "manos": list(v["manos_levantadas_por_zona"].values()),
        },
        columns=["zona", "manos"],
    )
    return screen, hands


def video_people_series(session: Session, bin_s: float = 30.0) -> pd.DataFrame:
    """Personas que MediaPipe ve a lo largo del vídeo (media por tramo de `bin_s` segundos)."""
    frames = (session.video or {}).get("personas_por_fotograma", [])
    cols = ["minuto", "personas"]
    if not frames:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(frames, columns=["t", "n"])
    df["minuto"] = (df["t"] // bin_s) * bin_s / 60
    out = df.groupby("minuto", as_index=False)["n"].mean().round(2)
    return out.rename(columns={"n": "personas"})[cols]


def video_tracks_table(session: Session, top: int = 12) -> pd.DataFrame:
    """Las pistas (personas seguidas) con más tiempo en pantalla: tamaño, centralidad y género."""
    tracks = (session.video or {}).get("pistas", [])
    cols = ["pista", "minutos_en_pantalla", "tamano_medio", "centralidad", "genero_por_audio"]
    rows = [
        {
            "pista": t["pista"],
            "minutos_en_pantalla": round(t["tiempo_en_pantalla_s"] / 60, 2),
            "tamano_medio": t["tamano_medio"],
            "centralidad": t["centralidad_media"],
            "genero_por_audio": t["genero_por_audio"],
        }
        for t in tracks
    ]
    df = pd.DataFrame(rows, columns=cols)
    return df.sort_values("minutos_en_pantalla", ascending=False).head(top).reset_index(drop=True)


def video_tracks_with_totals(session: Session, top: int = 12) -> pd.DataFrame:
    """Pistas con más tiempo en pantalla y, al final, el total por género de todas las pistas."""
    tracks = video_tracks_table(session, top)
    v = session.video or {}
    total_s = sum(t["tiempo_en_pantalla_s"] for t in v.get("pistas", [])) or 1.0
    tracks.insert(2, "porcentaje", (tracks["minutos_en_pantalla"] * 60 / total_s * 100).round(1))
    seconds = v.get("tiempo_en_pantalla_por_genero_s", {})
    percent = v.get("tiempo_en_pantalla_por_genero_%", {})
    totals = pd.DataFrame(
        [
            {
                "pista": f"Total {g}",
                "minutos_en_pantalla": round(seconds.get(g, 0.0) / 60, 2),
                "porcentaje": percent.get(g, 0.0),
                "genero_por_audio": g,
            }
            for g in ("hombre", "mujer", "desconocido")
        ],
        columns=list(tracks.columns),
    )
    return pd.concat([tracks.astype({"pista": str}), totals], ignore_index=True)


def evolution_table(sessions: list[Session]) -> pd.DataFrame:
    """Una fila por sesión (ordenada por fecha si hay ficha, si no por id)."""
    rows = []
    for s in sessions:
        row = {"sesion": s.session_id, "fecha": (s.source or {}).get("fecha_evento", "")}
        for m in CARD_METRICS:
            r = s.metrics[m]
            row[m] = r.value if r.conclusive else None
        row["M14"] = row["M09"] = None  # aún no disponibles
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["fecha", "sesion"], ignore_index=True)


def evolution_gender_table(sessions: list[Session]) -> pd.DataFrame:
    """% de tiempo de palabra por género y sesión (existe aunque la métrica no sea concluyente)."""
    frames = [gender_time_table(s).assign(sesion=s.session_id) for s in sessions]
    return pd.concat(frames, ignore_index=True)[["sesion", "gender", "porcentaje"]]


def _reading(share: dict[str, float]) -> str:
    """Lectura prudente de la brecha: qué pasaría según cómo fueran las voces sin género."""
    w, m = share.get("mujer", 0.0), share.get("hombre", 0.0)
    rest = share.get("desconocido", 0.0) + share.get("sin_atribuir", 0.0)
    low, high = w - (m + rest), (w + rest) - m
    text = (
        f"Con el género asignado, las mujeres tienen el {w:.1f} % del tiempo de palabra y los "
        f"hombres el {m:.1f} %; el {rest:.1f} % no tiene género."
    )
    if rest < 1:
        return text + f" La brecha (mujeres − hombres) es de {w - m:+.1f} puntos."
    verdict = (
        "El sentido de la brecha podría cambiar según quiénes sean esas voces: no es concluyente "
        "hasta confirmarlas."
        if low <= 0 <= high
        else "El sentido de la brecha no cambiaría, pero su tamaño sí."
    )
    return (
        text + f" La brecha (mujeres − hombres) estaría entre {low:+.1f} y {high:+.1f} puntos "
        f"según cómo fueran esas voces. {verdict}"
    )
