"""Capa de datos del panel: lee los ficheros del análisis y calcula las cifras con `metrics/`.

Sin Streamlit aquí, para poder probarla. Nunca muestra nombres: cada voz es «Persona N».
Si falta una métrica (M09, M14), se informa como «no disponible todavía».
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from contracts import AnalysisTimeline, EventType
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
            )
        )
    if not sessions:
        for path in sorted(SYNTHETIC_DIR.glob("*.timeline.json")):
            tl = AnalysisTimeline.model_validate_json(path.read_text("utf-8"))
            sessions.append(Session(tl.video_id, tl, synthetic=True))
    for s in sessions:
        frame = timeline_to_frame(s.timeline)
        s.metrics = {m: run_metric(m, frame) for m in CARD_METRICS}
    return sessions


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
            }
        )
    return pd.DataFrame(
        rows, columns=["persona", "inicio_min", "duracion_s", "genero", "evidencia"]
    )


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


def report_html(session: Session) -> str:
    """Informe descargable de una sesión (HTML; se imprime a PDF desde el navegador)."""
    e = html.escape
    src = session.source or {}
    cards = "".join(
        f"<li><b>{e(c['titulo'])}</b>: {e(c['valor'])}</li>"
        for c in map(metric_card, session.metrics.values())
    )
    pending = "".join(
        f"<li>{e(k)} {e(v)}: no disponible todavía</li>" for k, v in PENDING_METRICS.items()
    )
    table = gender_time_table(session).to_html(index=False, border=0)
    s13 = session.metrics["M13"]
    ficha = (
        "SINTÉTICO: datos de ejemplo, no son una sesión real."
        if session.synthetic
        else e(src.get("cita") or SOURCE_NOTICE)
    )
    return (
        f"<!doctype html><meta charset='utf-8'><title>Informe {e(session.session_id)}</title>"
        f"<h1>Informe de la sesión {e(session.session_id)}</h1><p>{ficha}</p>"
        f"<h2>Métricas</h2><ul>{cards}{pending}</ul>"
        f"<h2>Tiempo de palabra por género</h2>{table}"
        f"<h2>Método y límites</h2><p>{e(METHOD_NOTICE)}</p>"
        f"<p>Tiempo sin atribuir: {s13.value if s13.conclusive else 'n/d'} %. "
        "Métricas en borrador pendientes de validación.</p>"
    )
