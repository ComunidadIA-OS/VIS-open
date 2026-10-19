from contracts import AnalysisEvent, AnalysisTimeline, EventType, GenderValue, Provenance, Speaker
from pipeline.analyze import NOTICE, analyze_timeline


def make():
    texts = [
        ("SPEAKER_00", "Tiene la palabra la señora Pérez."),
        ("SPEAKER_01", "Gracias. Hablaré de presupuestos."),
        ("SPEAKER_02", "Hoy hablaremos de la ley."),
    ]
    events = [
        AnalysisEvent(
            event_id=f"e{i}", type=EventType.SPEECH, start_s=i * 10, end_s=i * 10 + 8,
            speaker_id=sp, text=t, confidence=0.9, provenance=Provenance.AI_INFERRED,
        )
        for i, (sp, t) in enumerate(texts)
    ]  # fmt: skip
    return AnalysisTimeline(
        video_id="SINTETICO", duration_s=40,
        speakers=[Speaker(speaker_id=f"SPEAKER_0{i}") for i in range(3)], events=events,
    )  # fmt: skip


def test_analyze_assigns_summarises_and_flags_review():
    tl, review, summary = analyze_timeline(make())
    sp = {s.speaker_id: s.gender for s in tl.speakers}
    assert sp["SPEAKER_01"] == GenderValue.WOMAN and sp["SPEAKER_02"] == GenderValue.UNKNOWN
    assert {r.speaker_id for r in review} == {"SPEAKER_00", "SPEAKER_02"}
    by = {r["gender"]: r["seconds"] for r in summary["tiempo_por_genero"]}
    assert by["mujer"] == 8 and by["desconocido"] == 16
    assert summary["aviso"] == NOTICE and summary["voces_a_revision"] == 2
