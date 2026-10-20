"""Capa de datos del panel: lee los ficheros del análisis y calcula las cifras con `metrics/`.

Sin Streamlit aquí, para poder probarla. Nunca muestra nombres: cada voz es «Persona N».
Si falta una métrica (M09, M14), se informa como «no disponible todavía».
"""

from __future__ import annotations

import html
import json
import re
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
    "El género se asigna solo por pistas del lenguaje de la sesión, nunca por la cara ni la voz. "
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


def fmt_time(seconds: float) -> str:
    m, sec = divmod(int(seconds), 60)
    return f"{m}:{sec:02d}"


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


REPORT_CSS = (Path(__file__).parent / "report.css").read_text(encoding="utf-8")
GENDER_COLORS = {
    "mujer": "var(--m)",
    "hombre": "var(--h)",
    "desconocido": "var(--d)",
    "sin_atribuir": "var(--s)",
}


def _gender_bar(table: pd.DataFrame) -> str:
    parts = "".join(
        f"<div style='width:{r['porcentaje']}%;"
        f"background:{GENDER_COLORS.get(r['gender'], '#999')}'>{r['porcentaje']:.0f}%</div>"
        for _, r in table.iterrows()
        if r["porcentaje"] >= 1
    )
    legend = "".join(
        f"<span><i style='background:{c}'></i>{g.replace('_', ' ')}</span>"
        for g, c in GENDER_COLORS.items()
    )
    return f"<div class='bar'>{parts}</div><div class='leg'>{legend}</div>"


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


def _timeline_svg(session: Session) -> str:
    """Línea de tiempo de la sesión: un tramo coloreado por género (SVG sin dependencias)."""
    strip = timeline_strip(session).sort_values("inicio_min")
    end = max(float(session.timeline.duration_s) / 60, 0.01)
    rects = []
    for r in strip.itertuples():
        color = GENDER_COLORS.get(r.genero, "#e08a00")
        x, w = 100 * r.inicio_min / end, max(100 * (r.fin_min - r.inicio_min) / end, 0.08)
        rects.append(f"<rect x='{x:.3f}' y='0' width='{w:.3f}' height='30' fill='{color}'/>")
    ticks = "".join(
        f"<text x='{100 * m / end:.2f}' y='46' font-size='3.2'>{m} min</text>"
        for m in range(0, int(end) + 1, max(1, int(end // 8)))
    )
    return (
        "<svg viewBox='0 0 100 50' preserveAspectRatio='none' width='100%' height='80'>"
        f"{''.join(rects)}{ticks}</svg>"
    )


def report_html(session: Session) -> str:
    """Informe descargable de una sesión (HTML autónomo; se imprime a PDF desde el navegador)."""
    e = html.escape
    src = session.source or {}
    tl = session.timeline
    gt = gender_time_table(session)
    share = dict(zip(gt["gender"], gt["porcentaje"], strict=True))
    voices = voices_table(session)
    known = int((voices["genero"] != "desconocido").sum())
    confirmed = len(session.confirmed)
    ficha = (
        "SINTÉTICO: datos de ejemplo, no son una sesión real."
        if session.synthetic
        else e(src.get("cita") or SOURCE_NOTICE)
    )
    cards = "".join(
        f"<div class='card'><span>{e(c['titulo'].split(' (')[0])}</span>"
        f"<b>{e(c['valor'])}</b></div>"
        for c in map(metric_card, session.metrics.values())
    )
    pending = "".join(
        f"<li>{e(k)} {e(v)}: no disponible todavía</li>" for k, v in PENDING_METRICS.items()
    )
    summary = (
        f"Sesión de {tl.duration_s / 60:.0f} minutos con {len(voices)} voces, de las que "
        f"{known} tienen género asignado"
        + (f" ({confirmed} confirmadas por dos anotadoras)" if confirmed else "")
        + f". {_reading(share)}"
    )
    voices_rows = "".join(
        f"<tr><td>{e(r.persona)}</td><td>{e(r.genero)}</td><td>{e(r.origen)}</td>"
        f"<td>{r.minutos}</td><td>{r.intervenciones}</td></tr>"
        for r in voices.itertuples()
    )
    inter = interventions_table(session)
    interventions = inter.drop(columns=["evidencia"]).to_html(index=False, border=0)
    transcript = "".join(
        f"<p><b>{fmt_time(t['inicio_s'])} · {e(t['persona'])} · {e(t['genero'])}</b><br>"
        f"{e(t['texto'])}</p>"
        for t in transcript_turns(session)
    )
    video = ""
    if video_tables(session):
        v = session.video
        pct = v["tiempo_en_pantalla_por_genero_%"]
        screen = pd.DataFrame({"gender": list(pct), "porcentaje": list(pct.values())})
        hands = v.get("manos_levantadas_por_zona", {})
        video = (
            "<h2>Análisis de vídeo (sin caras)</h2>"
            f"<div class='warn'>{e(v['aviso'])}</div>"
            f"<p>Personas visibles a la vez: máximo {v['personas_visibles_max']}, mediana "
            f"{v['personas_visibles_mediana']}; fotogramas sin nadie: "
            f"{v['fotogramas_sin_personas_%']} %.</p><p>Tiempo en pantalla por género "
            "(el género sale del audio):</p>"
            + _gender_bar(screen)
            + "<p>Manos levantadas por zona: "
            + (", ".join(f"{e(z)}: {n}" for z, n in hands.items()) or "ninguna detectada")
            + ".</p>"
            + "<p>Momentos: "
            + (
                ", ".join(
                    f"{fmt_time(h['inicio_s'])} (zona {e(h['zona'])})"
                    for h in v.get("manos_levantadas", [])
                )
                or "ninguno"
            )
            + ".</p>"
        )
    return (
        "<!doctype html><html lang='es'><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>Informe {e(session.session_id)}</title><style>{REPORT_CSS}</style>"
        f"<h1>Informe de la sesión {e(session.session_id)}</h1><p class='sub'>{ficha}</p>"
        f"<h2>Resumen</h2><div class='note'>{e(summary)}</div>"
        f"<h2>Métricas</h2><div class='grid'>{cards}</div><ul>{pending}</ul>"
        f"<h2>Tiempo de palabra por género</h2>{_gender_bar(gt)}"
        f"{gt.to_html(index=False, border=0)}"
        f"<h2>Línea de tiempo</h2>{_timeline_svg(session)}"
        "<h2>Voces</h2><table><tr><th>Persona</th><th>Género</th><th>Origen</th>"
        f"<th>Minutos</th><th>Intervenciones</th></tr>{voices_rows}</table>"
        f"{video}"
        f"<h2>Intervenciones</h2>{interventions}"
        f"<h2>Transcripción</h2><details><summary>Ver la transcripción seudonimizada</summary>"
        f"{transcript}</details>"
        f"<h2>Método y límites</h2><p>{e(METHOD_NOTICE)}</p>"
        "<ul><li>El género sale solo del texto o de la confirmación de dos anotadoras "
        "(Human in the loop); nunca de la cara ni del sonido.</li>"
        "<li>Las voces sin pista clara figuran como «desconocido» y pasan a revisión humana.</li>"
        "<li>Métricas en borrador pendientes de validación.</li></ul>"
        "<footer>VIS Open · cifras calculadas por código · sin nombres, sin caras.</footer></html>"
    )
