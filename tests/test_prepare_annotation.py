"""Hoja de anotación: turnos, muestra equilibrada y que la hoja no filtre el género del sistema."""

import csv

from contracts import AnalysisEvent, AnalysisTimeline, EventType, Provenance, Speaker
from evaluation.prepare_annotation import build_turns, main, sample_turns


def timeline():
    def ev(i, start, end, spk, text):
        return AnalysisEvent(
            event_id=f"ev{i}", type=EventType.SPEECH, start_s=start, end_s=end,
            speaker_id=spk, text=text, provenance=Provenance.AI_INFERRED,
        )  # fmt: skip

    events = [
        ev(0, 0, 3, "SPEAKER_00", "Tiene la palabra la señora Persona 2."),
        ev(1, 3.5, 6, "SPEAKER_01", "Gracias presidente, buenos días a todos"),
        ev(2, 6.5, 9, "SPEAKER_01", "y a todas las personas presentes hoy."),  # mismo turno
        ev(3, 20, 24, "SPEAKER_01", "Otro turno de la misma voz mucho después."),
    ]
    speakers = [
        Speaker(speaker_id="SPEAKER_00"),
        Speaker(speaker_id="SPEAKER_01", gender="mujer", gender_source="pista_lenguaje"),
    ]
    return AnalysisTimeline(video_id="V", duration_s=30, speakers=speakers, events=events)


def test_consecutive_segments_of_one_voice_merge_and_context_is_previous_turn():
    turns = build_turns(timeline())
    assert len(turns) == 3
    assert turns[1].text.endswith("personas presentes hoy.") and turns[1].gender == "mujer"
    assert turns[1].context_before.startswith("Tiene la palabra")
    assert turns[2].context_before.endswith("hoy.")


def test_sample_is_seeded_balanced_and_skips_short_turns():
    turns = build_turns(timeline())
    a = sample_turns(turns, 1, {"mujer": 5, "desconocido": 5})
    assert [t.event_id for t in a] == [
        t.event_id for t in sample_turns(turns, 1, {"mujer": 5, "desconocido": 5})
    ]
    assert {t.gender for t in a} == {"mujer", "desconocido"} and len(a) == 3  # todos ≥ 6 palabras


def test_cli_sheet_has_no_system_gender_and_key_is_separate(tmp_path):
    folder = tmp_path / "processed" / "V"
    folder.mkdir(parents=True)
    (folder / "timeline.json").write_text(timeline().model_dump_json(), encoding="utf-8")
    out = tmp_path / "anot"
    main(["--data", str(tmp_path), "--out", str(out)])
    sheet = list(csv.DictReader((out / "turnos_para_anotar.csv").open(encoding="utf-8")))
    assert list(sheet[0]) == ["turn_id", "context_before", "text", "label"]
    assert all(r["label"] == "" for r in sheet)
    key = list(csv.DictReader((out / "clave_interna.csv").open(encoding="utf-8")))
    assert {r["genero_sistema"] for r in key} <= {"mujer", "hombre", "desconocido"}
    assert "genero_sistema" not in (out / "turnos_para_anotar.csv").read_text(encoding="utf-8")
