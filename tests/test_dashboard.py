"""Panel: capa de datos y carga de la app con datos SINTÉTICOS (sin sesiones reales)."""

from pathlib import Path

import pytest

from dashboard.data import (
    evolution_table,
    interventions_table,
    load_sessions,
    metric_card,
    report_html,
)

APP = Path(__file__).parent.parent / "dashboard" / "app.py"


@pytest.fixture
def sessions(tmp_path):
    return load_sessions(tmp_path)  # carpeta vacía → muestras sintéticas del repositorio


def test_falls_back_to_synthetic_and_computes_cards(sessions):
    assert len(sessions) == 5 and all(s.synthetic for s in sessions)
    by = {s.session_id: s for s in sessions}
    assert (
        metric_card(by["SINTETICO_muestra_insuficiente"].metrics["M02"])["valor"]
        == "no concluyente"
    )
    assert metric_card(by["SINTETICO_pocas_mujeres"].metrics["M04"])["valor"] != "no concluyente"


def test_interventions_never_show_names_only_codes(sessions):
    t = interventions_table(sessions[0])
    assert set(t["persona"]) <= {f"Persona {i}" for i in range(1, 10)} | {"sin atribuir"}
    unk = next(s for s in sessions if s.session_id.endswith("con_desconocidos"))
    assert "desconocido" in set(interventions_table(unk)["genero"])


def test_evolution_and_report(sessions):
    evo = evolution_table(sessions)
    assert len(evo) == 5 and {"M01", "M02", "M03", "M04", "M13", "M14", "M09"} <= set(evo.columns)
    html = report_html(sessions[0])
    assert "SINTÉTICO" in html and "Método y límites" in html and "no disponible todavía" in html


def test_real_session_folder_is_read(tmp_path):
    import shutil

    from dashboard.data import SYNTHETIC_DIR

    d = tmp_path / "processed" / "V001"
    d.mkdir(parents=True)
    shutil.copy(SYNTHETIC_DIR / "SINTETICO_equilibrado.timeline.json", d / "timeline.json")
    (d / "source.json").write_text('{"cita": "Fuente: X", "fecha_evento": "2026-10-16"}', "utf-8")
    s = load_sessions(tmp_path)
    assert [x.session_id for x in s] == ["V001"] and not s[0].synthetic
    assert "Fuente: X" in report_html(s[0])


def test_app_loads_without_errors(tmp_path, monkeypatch):
    at_mod = pytest.importorskip("streamlit.testing.v1")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    at = at_mod.AppTest.from_file(str(APP), default_timeout=60).run()
    assert not at.exception
    assert any("SINTÉTICO" in w.value for w in at.warning)
    at.sidebar.radio[0].set_value("Evolución").run()
    assert not at.exception


def test_video_tables_none_without_video_and_shown_with_it(tmp_path, sessions):
    import json

    from dashboard.data import video_tables

    assert video_tables(sessions[0]) is None
    folder = tmp_path / "processed" / "V9"
    folder.mkdir(parents=True)
    tl = (Path(__file__).parent.parent / "evaluation/synthetic/muestras").glob("*.timeline.json")
    (folder / "timeline.json").write_text(next(iter(tl)).read_text("utf-8"), encoding="utf-8")
    (folder / "video.json").write_text(
        json.dumps(
            {
                "aviso": "x",
                "tiempo_en_pantalla_por_genero_s": {"mujer": 60.0, "hombre": 120.0},
                "tiempo_en_pantalla_por_genero_%": {"mujer": 33.3, "hombre": 66.7},
                "manos_levantadas_por_zona": {},
            }
        ),
        encoding="utf-8",
    )
    screen, hands = video_tables(load_sessions(tmp_path)[0])
    assert list(screen["minutos"]) == [1.0, 2.0] and hands.empty


def test_video_path_only_when_the_file_is_local(tmp_path, sessions):
    from dashboard.data import video_path

    s = sessions[0]
    assert video_path(s, tmp_path) is None
    (tmp_path / "raw").mkdir()
    (tmp_path / "raw" / f"{s.session_id}.mp4").write_bytes(b"x")
    assert video_path(s, tmp_path) == tmp_path / "raw" / f"{s.session_id}.mp4"


def _review_folder(tmp_path):
    from contracts import ReviewRow, write_rows

    folder = tmp_path / "processed" / "V9"
    folder.mkdir(parents=True)
    rows = [
        ReviewRow(video_id="V9", speaker_id="SPEAKER_00", total_seconds=10),
        ReviewRow(video_id="V9", speaker_id="SPEAKER_01", total_seconds=20),
    ]
    write_rows(rows, ReviewRow, folder / "review_genero.csv")
    return folder


def test_two_annotators_must_agree_and_confirmed_gender_is_applied(tmp_path):
    from contracts import AnalysisTimeline, Speaker
    from dashboard.data import agreed_genders, apply_confirmed, save_review

    folder = _review_folder(tmp_path)
    save_review(folder, 1, "SPEAKER_00", "mujer", "alta", "", "ID-1")
    assert agreed_genders(folder) == {}  # solo una anotadora
    save_review(folder, 2, "SPEAKER_00", "mujer", "media", "", "ID-2")
    save_review(folder, 1, "SPEAKER_01", "hombre", "alta", "", "ID-1")
    save_review(folder, 2, "SPEAKER_01", "mujer", "alta", "", "ID-2")  # no coinciden
    assert agreed_genders(folder) == {"SPEAKER_00": "mujer"}
    tl = AnalysisTimeline(
        video_id="V9",
        duration_s=30,
        speakers=[Speaker(speaker_id="SPEAKER_00"), Speaker(speaker_id="SPEAKER_01")],
    )
    out = apply_confirmed(tl, {"SPEAKER_00": "mujer"})
    assert [s.gender.value for s in out.speakers] == ["mujer", "desconocido"]
    assert out.speakers[0].gender_source.value == "anotacion_percibida"


def test_save_review_rejects_unknown_voice(tmp_path):
    import pytest as _pytest

    from dashboard.data import save_review

    with _pytest.raises(ValueError):
        save_review(_review_folder(tmp_path), 1, "SPEAKER_99", "mujer", "alta", "", "ID-1")


def test_voice_blocks_and_time_format():
    from contracts import AnalysisEvent, AnalysisTimeline, Speaker
    from dashboard.data import fmt_time, voice_blocks

    def ev(i, a, b):
        return AnalysisEvent(
            event_id=f"e{i}", type="speech", start_s=a, end_s=b, speaker_id="SPEAKER_00",
            text="x", provenance="ai_inferred",
        )  # fmt: skip

    tl = AnalysisTimeline(
        video_id="V",
        duration_s=300,
        speakers=[Speaker(speaker_id="SPEAKER_00")],
        events=[ev(0, 0, 10), ev(1, 11, 20), ev(2, 100, 105), ev(3, 200, 230)],
    )
    assert voice_blocks(tl, "SPEAKER_00", top=2) == [(0, 20), (200, 230)]
    assert fmt_time(178) == "2:58" and fmt_time(5) == "0:05"


def test_evolution_gender_table_has_every_session_even_without_conclusive_metrics(sessions):
    from dashboard.data import evolution_gender_table

    t = evolution_gender_table(sessions)
    assert set(t["sesion"]) == {s.session_id for s in sessions}
    assert list(t.columns) == ["sesion", "gender", "porcentaje"]


def test_transcript_turns_merge_same_voice_and_use_codes(sessions):
    from dashboard.data import transcript_turns

    turns = transcript_turns(sessions[0])
    assert turns and set(turns[0]) == {"inicio_s", "speaker_id", "persona", "genero", "texto"}
    assert all(t["persona"].startswith("Persona ") or t["persona"] == "sin atribuir" for t in turns)
    assert len(turns) <= sum(1 for e in sessions[0].timeline.events if e.text)


def test_same_person_cannot_confirm_twice_and_bad_connection_id_is_refused(tmp_path):
    import pytest as _pytest

    from dashboard.data import agreed_genders, save_review, valid_connection_id

    folder = _review_folder(tmp_path)
    save_review(folder, 1, "SPEAKER_00", "mujer", "alta", "", "ID-1")
    save_review(folder, 2, "SPEAKER_00", "mujer", "alta", "", "ID-1")  # mismo ID en los dos
    assert agreed_genders(folder) == {}
    assert not valid_connection_id("Ana García") and valid_connection_id("ID-2")
    with _pytest.raises(ValueError):
        save_review(folder, 1, "SPEAKER_00", "mujer", "alta", "", "ana@correo.es")


def test_default_annotator_slots_are_valid_distinct_ids(tmp_path):
    from dashboard.data import agreed_genders, save_review

    folder = _review_folder(tmp_path)
    for n in (1, 2):  # sin acceso con usuarios, la app guarda como «anotadora_N»
        save_review(folder, n, "SPEAKER_00", "hombre", "alta", "", f"anotadora_{n}")
    assert agreed_genders(folder) == {"SPEAKER_00": "hombre"}


def test_voices_table_has_one_row_per_voice_with_minutes_and_origin(sessions):
    from dashboard.data import voices_table

    s = sessions[0]
    t = voices_table(s)
    assert len(t) == len(s.timeline.speakers)
    assert list(t.columns) == [
        "persona", "genero", "origen", "minutos", "intervenciones", "evidencia",
    ]  # fmt: skip
    assert t["minutos"].is_monotonic_decreasing


def test_report_has_summary_timeline_voices_and_prudent_reading(sessions):
    h = report_html(sessions[0])
    for part in ("Resumen", "Línea de tiempo", "<svg", "Voces", "Intervenciones", "Transcripción"):
        assert part in h
    from dashboard.data import _reading

    assert "podría cambiar" in _reading({"mujer": 20.0, "hombre": 50.0, "desconocido": 30.0})
    assert "no cambiaría" in _reading({"mujer": 10.0, "hombre": 80.0, "desconocido": 10.0})
    assert "+" in _reading({"mujer": 50.0, "hombre": 50.0})


def test_voice_transcripts_csv_and_export_link_to_the_csv(sessions, tmp_path):
    import csv as _csv

    from dashboard.data import export_session, transcript_csv, voice_transcripts

    s = sessions[0]
    by_voice = voice_transcripts(s)
    assert by_voice and all(k.startswith("Persona ") or k == "sin atribuir" for k in by_voice)
    rows = list(_csv.DictReader(transcript_csv(s).splitlines()))
    assert rows and list(rows[0]) == ["inicio_s", "inicio", "persona", "genero", "texto"]
    report, table = export_session(s, tmp_path, link_base="https://almacen.example/privado/")
    assert table.name == f"transcripcion_{s.session_id}.csv" and table.is_file()
    html_text = report.read_text(encoding="utf-8")
    assert f"https://almacen.example/privado/transcripcion_{s.session_id}.csv" in html_text
    assert "<details>" in html_text  # cada voz se despliega


def test_inconclusive_metrics_explain_why(sessions):
    from dashboard.data import inconclusive_reason

    by = {s.session_id: s for s in sessions}
    assert "muestra insuficiente" in inconclusive_reason(by["SINTETICO_muestra_insuficiente"])
    assert "Por qué" in report_html(by["SINTETICO_muestra_insuficiente"])
    assert inconclusive_reason(by["SINTETICO_pocas_mujeres"]) == ""
