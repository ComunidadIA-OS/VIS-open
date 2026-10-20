import json

from contracts import AnalysisEvent, AnalysisTimeline, EventType, Provenance, Speaker
from pipeline.reanalyze import reanalyze


def test_reanalyze_rewrites_outputs_without_names(tmp_path):
    ev = [
        AnalysisEvent(
            event_id=f"e{i}", type=EventType.SPEECH, start_s=i * 5, end_s=i * 5 + 4,
            speaker_id=sp, text=t, confidence=0.9, provenance=Provenance.AI_INFERRED,
        )
        for i, (sp, t) in enumerate(
            [
                ("SPEAKER_00", "Tiene la palabra la señora Luna Ortega."),
                ("SPEAKER_01", "Gracias, Andrea."),
            ]
        )
    ]  # fmt: skip
    tl = AnalysisTimeline(
        video_id="SINTETICO", duration_s=12,
        speakers=[Speaker(speaker_id="SPEAKER_00"), Speaker(speaker_id="SPEAKER_01")], events=ev,
    )  # fmt: skip
    (tmp_path / "timeline.json").write_text(tl.model_dump_json(), encoding="utf-8")
    paths = reanalyze(tmp_path)
    blob = "".join(p.read_text(encoding="utf-8") for p in paths)
    assert "Luna" not in blob and "Ortega" not in blob and "Andrea" not in blob
    assert json.loads(paths[1].read_text(encoding="utf-8"))["voces"]["SPEAKER_01"] == "Persona 2"
