"""Paso posterior a la línea de tiempo: género por lenguaje y resumen de tiempo de palabra.

No define métricas M01 a M13 (son de Ivette): solo el tiempo de palabra por género, con la
muestra y el aviso de método que debe llevar todo informe.
"""

from __future__ import annotations

from contracts import AnalysisTimeline, ReviewRow
from decision import (
    CueRules,
    apply_assignments,
    assign_genders,
    build_gender_review_rows,
    load_rules,
)
from decision.pseudonymize import pseudonymize_timeline
from metrics import sample_of, speech_time_by_gender, timeline_to_frame

NOTICE = (
    "El género se atribuye por pistas del lenguaje de la transcripción (nunca por cara, voz ni "
    "tono); las voces sin pista clara figuran como «desconocido» y pasan a revisión humana. "
    "Cifras calculadas por código; indicadores de apoyo, no veredictos."
)


def analyze_timeline(
    timeline: AnalysisTimeline, annotator_id: str = "anotadora_1", rules: CueRules | None = None
) -> tuple[AnalysisTimeline, list[ReviewRow], dict]:
    """Devuelve (línea de tiempo sin nombres y con género, filas de revisión, resumen)."""
    timeline, codes = pseudonymize_timeline(timeline)  # primero: ningún nombre llega a la salida
    assignments = assign_genders(timeline, rules or load_rules("es"))
    enriched = apply_assignments(timeline, assignments)
    review = build_gender_review_rows(timeline, assignments, annotator_id)
    frame = timeline_to_frame(enriched)
    sample = sample_of(frame)
    summary = {
        "video_id": timeline.video_id,
        "aviso": NOTICE,
        "tiempo_por_genero": speech_time_by_gender(frame).to_dict(orient="records"),
        "muestra": {
            "n_eventos_habla": sample.n_events,
            "n_voces": sample.n_speakers,
            "n_voces_genero_conocido": sample.n_speakers_known_gender,
            "segundos_habla": round(sample.speech_seconds, 3),
            "proporcion_sin_atribuir": round(sample.unattributed_share, 4),
        },
        "voces": codes,
        "voces_a_revision": len(review),
    }
    return enriched, review, summary
