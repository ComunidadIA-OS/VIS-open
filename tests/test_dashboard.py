"""Panel: capa de datos y carga de la app con datos SINTÉTICOS (sin sesiones reales)."""

from pathlib import Path

import pytest

from dashboard.data import (
    evolution_table,
    interventions_table,
    load_sessions,
    metric_card,
)
from dashboard.pdf_report import report_pdf

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
    # 2 mujeres y 2 hombres: M04 sí puede comparar.
    assert metric_card(by["SINTETICO_equilibrado"].metrics["M04"])["valor"] != "no concluyente"
    # 1 sola mujer: no hay 2 voces en el grupo, así que M04 no concluye (§4 ter).
    assert metric_card(by["SINTETICO_pocas_mujeres"].metrics["M04"])["valor"] == "no concluyente"


def test_synthetic_sessions_get_question_blocks_from_the_text(sessions):
    s = next(x for x in sessions if x.session_id.endswith("equilibrado"))
    assert s.metrics["M03a"].conclusive is True
    assert s.metrics["M03a"].details["preguntas"] > 0
    assert s.metrics["M03b"].conclusive is True
    assert s.metrics["M03b"].details["preguntas"] > 0
    assert s.metrics["M04"].conclusive is True


def test_metric_card_says_not_applicable_without_question_blocks():
    from metrics import MetricResult

    r = MetricResult(
        metric_id="M03a", name="M03a Intervenciones", is_example=False, value=None,
        conclusive=False,
        reason="no aplica: no se han detectado bloques de pregunta", sample={},
    )  # fmt: skip
    assert metric_card(r)["valor"] == "no aplica"


def test_inconclusive_reason_ignores_metrics_that_do_not_apply():
    from contracts import AnalysisTimeline
    from dashboard.data import SYNTHETIC_DIR, Session, inconclusive_reason
    from metrics import MetricResult

    tl = AnalysisTimeline.model_validate_json(
        (SYNTHETIC_DIR / "SINTETICO_equilibrado.timeline.json").read_text("utf-8")
    )
    s = Session(
        "X", tl,
        metrics={
            "M03a": MetricResult(
                metric_id="M03a", name="M03a", is_example=False, value=None,
                conclusive=False, reason="no aplica: sin bloques", sample={},
            )
        },
    )  # fmt: skip
    assert inconclusive_reason(s) == ""
    s.metrics["M02"] = MetricResult(
        metric_id="M02", name="M02", is_example=False, value=None,
        conclusive=False, reason="no concluyente: muestra insuficiente", sample={},
    )  # fmt: skip
    assert "muestra insuficiente" in inconclusive_reason(s)


def test_m09_and_m06_are_read_from_m09_json(tmp_path):
    import json
    import shutil

    from dashboard.data import SYNTHETIC_DIR

    folder = tmp_path / "processed" / "V001"
    folder.mkdir(parents=True)
    shutil.copy(SYNTHETIC_DIR / "SINTETICO_equilibrado.timeline.json", folder / "timeline.json")
    payload = {
        "preguntas": 30,
        "M09": {"metric_id": "M09", "name": "M09 Preguntas recibidas",
                "is_example": False, "value": 1.0, "conclusive": True,
                "sample": {}, "details": {}},
        "M06": {"metric_id": "M06", "name": "M06 Preguntas al Presidente",
                "is_example": False, "value": 50.0, "conclusive": True,
                "sample": {}, "details": {}},
    }  # fmt: skip
    (folder / "m09.json").write_text(json.dumps(payload), "utf-8")
    s = load_sessions(tmp_path)[0]
    assert {"M09", "M06", "M02b"} <= set(s.metrics)
    assert metric_card(s.metrics["M09"])["valor"] == "1"
    assert metric_card(s.metrics["M06"])["valor"] == "50"


def test_m09_is_no_longer_pending():
    from dashboard.data import PENDING_METRICS

    assert "M09" not in PENDING_METRICS and "M14" not in PENDING_METRICS  # M14 descartada


def test_interventions_never_show_names_only_codes(sessions):
    t = interventions_table(sessions[0])
    assert set(t["persona"]) <= {f"Persona {i}" for i in range(1, 10)} | {"sin atribuir"}
    unk = next(s for s in sessions if s.session_id.endswith("con_desconocidos"))
    assert "desconocido" in set(interventions_table(unk)["genero"])


def test_evolution_and_report(sessions):
    evo = evolution_table(sessions)
    assert len(evo) == 5 and {
        "M01", "M02", "M03a", "M03b", "M04", "M13", "M09"
    } <= set(evo.columns)
    assert "M14" not in evo.columns
    pdf = report_pdf(sessions[0], compress=False)
    assert pdf.startswith(b"%PDF") and b"datos de ejemplo" in pdf and b"Resumen" in pdf


def test_real_session_folder_is_read(tmp_path):
    import shutil

    from dashboard.data import SYNTHETIC_DIR

    d = tmp_path / "processed" / "V001"
    d.mkdir(parents=True)
    shutil.copy(SYNTHETIC_DIR / "SINTETICO_equilibrado.timeline.json", d / "timeline.json")
    (d / "source.json").write_text('{"cita": "Fuente: X", "fecha_evento": "2026-10-16"}', "utf-8")
    s = load_sessions(tmp_path)
    assert [x.session_id for x in s] == ["V001"] and not s[0].synthetic
    assert b"Fuente: X" in report_pdf(s[0], compress=False)


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
    words = "Señora ministra, le pregunto por los alquileres."
    applause = AnalysisTimeline(
        video_id="A",
        duration_s=300,
        speakers=[Speaker(speaker_id="SPEAKER_00")],
        events=[ev(0, 0, 40).model_copy(update={"text": "(Aplausos)"}),
                ev(1, 100, 110).model_copy(update={"text": words})],
    )  # fmt: skip
    assert voice_blocks(applause, "SPEAKER_00", top=1) == [(100, 110)]  # sin el tramo de aplausos
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
    pdf = report_pdf(sessions[0], compress=False)
    for part in (b"Resumen", b"Voces", b"Persona", b"transcripcion_"):
        assert part in pdf
    from dashboard.data import _reading

    assert "podría cambiar" in _reading({"mujer": 20.0, "hombre": 50.0, "desconocido": 30.0})
    assert "no cambiaría" in _reading({"mujer": 10.0, "hombre": 80.0, "desconocido": 10.0})
    assert "+" in _reading({"mujer": 50.0, "hombre": 50.0})
    # 2 × M02 − 100 (metricas.md): V006 con 36,5 / 52,8 / 10,7 → −18,3, no −16,3
    assert "−18,3" in _reading({"mujer": 36.5, "hombre": 52.8, "desconocido": 10.7}).replace(
        "-", "−"
    ).replace(".", ",")


def test_voice_transcripts_csv_and_export_link_to_the_csv(sessions, tmp_path):
    import csv as _csv

    from dashboard.data import transcript_csv, voice_transcripts
    from dashboard.export import export_session

    s = sessions[0]
    by_voice = voice_transcripts(s)
    assert by_voice and all(k.startswith("Persona ") or k == "sin atribuir" for k in by_voice)
    rows = list(_csv.DictReader(transcript_csv(s).splitlines()))
    assert rows and list(rows[0]) == ["inicio_s", "inicio", "persona", "genero", "texto"]
    report, table = export_session(s, tmp_path, link_base="https://almacen.example/privado/")
    assert table.name == f"transcripcion_{s.session_id}.csv" and table.is_file()
    assert report.name == f"informe_{s.session_id}.pdf" and report.read_bytes().startswith(b"%PDF")
    link = f"https://almacen.example/privado/transcripcion_{s.session_id}.csv"
    assert link.encode() in report_pdf(s, link, compress=False)  # el PDF enlaza al CSV


def test_inconclusive_metrics_explain_why(sessions):
    from dashboard.data import inconclusive_reason

    by = {s.session_id: s for s in sessions}
    assert "muestra insuficiente" in inconclusive_reason(by["SINTETICO_muestra_insuficiente"])
    assert b"muestra insuficiente" in report_pdf(
        by["SINTETICO_muestra_insuficiente"], compress=False
    )
    assert "menos de 2 voces por grupo" in inconclusive_reason(by["SINTETICO_pocas_mujeres"])


def test_tracks_table_ends_with_totals_by_gender(tmp_path):
    import json

    from dashboard.data import video_tracks_with_totals

    folder = tmp_path / "processed" / "V9"
    folder.mkdir(parents=True)
    tl = next(
        (Path(__file__).parent.parent / "evaluation/synthetic/muestras").glob("*.timeline.json")
    )
    (folder / "timeline.json").write_text(tl.read_text("utf-8"), encoding="utf-8")
    pistas = [
        {"pista": 1, "tiempo_en_pantalla_s": 120.0, "tamano_medio": 0.2, "centralidad_media": 0.9,
         "genero_por_audio": "hombre", "votos_audio": {}},
        {"pista": 2, "tiempo_en_pantalla_s": 60.0, "tamano_medio": 0.3, "centralidad_media": 0.8,
         "genero_por_audio": "mujer", "votos_audio": {}},
    ]  # fmt: skip
    (folder / "video.json").write_text(
        json.dumps(
            {
                "aviso": "x", "pistas": pistas,
                "tiempo_en_pantalla_por_genero_s": {"hombre": 120, "mujer": 60, "desconocido": 0},
                "tiempo_en_pantalla_por_genero_%": {
                    "hombre": 66.7, "mujer": 33.3, "desconocido": 0,
                },
            }
        ),
        encoding="utf-8",
    )  # fmt: skip
    t = video_tracks_with_totals(load_sessions(tmp_path)[0])
    assert list(t["pista"]) == ["1", "2", "Total hombre", "Total mujer", "Total desconocido"]
    assert list(t["porcentaje"]) == [66.7, 33.3, 66.7, 33.3, 0.0]
    assert list(t["minutos_en_pantalla"])[-3:] == [2.0, 1.0, 0.0]


def test_make_clip_cuts_only_the_requested_seconds(tmp_path):
    import shutil
    import subprocess

    import pytest as _pytest

    from dashboard.data import make_clip

    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        _pytest.skip("hace falta FFmpeg")
    src = tmp_path / "src.mp4"
    subprocess.run(  # vídeo de prueba de 6 s generado por FFmpeg, no es un vídeo real
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=160x90:rate=10",
         "-t", "6", "-pix_fmt", "yuv420p", str(src)],
        check=True,
    )  # fmt: skip
    clip = make_clip(src, 2.0, 5.0, tmp_path / "clips", "S_SPEAKER_00")
    assert clip is not None and clip.name == "S_SPEAKER_00_2_5.mp4"
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(clip)],
        capture_output=True, text=True, check=True,
    )  # fmt: skip
    assert 2.5 < float(out.stdout) < 3.5
    assert make_clip(src, 3.0, 3.0, tmp_path / "clips", "x") is None


def test_screen_tables_use_minutes_and_percent_format():
    import pandas as pd

    from dashboard.data import show_interventions, show_tracks, show_voices

    rows = pd.DataFrame(
        {"persona": ["Persona 1"], "inicio_min": [1.5], "duracion_s": [7.3],
         "genero": ["mujer"], "texto": ["hola"]}
    )  # fmt: skip
    out = show_interventions(rows)
    assert out.loc[0, "inicio (min:s)"] == "1:30" and out.loc[0, "duración (min:s)"] == "0:07"
    voices = pd.DataFrame(
        {"persona": ["Persona 1"], "genero": ["hombre"], "origen": ["x"],
         "minutos": [13.65], "intervenciones": [4]}
    )  # fmt: skip
    assert show_voices(voices).loc[0, "tiempo de palabra (min:s)"] == "13:39"
    tracks = pd.DataFrame(
        {"pista": ["1"], "minutos_en_pantalla": [10.06], "porcentaje": [11.9],
         "tamano_medio": [float("nan")], "centralidad": [0.5], "genero_por_audio": ["mujer"]}
    )  # fmt: skip
    shown = show_tracks(tracks)
    assert (
        shown.loc[0, "tiempo en pantalla"] == "10:03" and shown.loc[0, "% del tiempo"] == "11.9 %"
    )
    assert shown.loc[0, "tamaño medio (% de la imagen)"] == ""


def test_review_cuts_are_listed_one_after_another_and_one_answer_covers_the_voice(tmp_path):
    from contracts import AnalysisEvent, AnalysisTimeline, Speaker
    from dashboard.data import (
        SAMPLE_S,
        Session,
        annotator_answers,
        cut_text,
        review_cuts,
        save_review,
    )

    def ev(i, start, end, spk, text):
        return AnalysisEvent(
            event_id=f"e{i}", type="speech", start_s=start, end_s=end, speaker_id=spk,
            text=text, provenance="ai_inferred",
        )  # fmt: skip

    events = [
        ev(0, 0, 20, "SPEAKER_00", "primero de la voz cero"),
        ev(1, 100, 130, "SPEAKER_01", "de la voz uno"),
        ev(2, 200, 215, "SPEAKER_00", "segundo de la voz cero"),
        ev(3, 300, 302, "SPEAKER_00", "demasiado corto"),
    ]
    tl = AnalysisTimeline(
        video_id="V9", duration_s=400,
        speakers=[Speaker(speaker_id="SPEAKER_00"), Speaker(speaker_id="SPEAKER_01")],
        events=events,
    )  # fmt: skip
    session = Session("V9", tl)
    cuts = review_cuts(session, ["SPEAKER_00", "SPEAKER_01"])
    assert [(c["speaker_id"], c["start"]) for c in cuts] == [
        ("SPEAKER_00", 0),
        ("SPEAKER_00", 200),
        ("SPEAKER_01", 100),
    ]  # fmt: skip  (agrupados por voz)
    assert all(float(c["stop"]) - float(c["start"]) <= SAMPLE_S for c in cuts)
    assert (
        "primero" in cuts[0]["texto"] and cut_text(tl, "SPEAKER_00", 300, 302) == "demasiado corto"
    )

    folder = _review_folder(tmp_path)
    assert annotator_answers(folder, 1) == {}
    save_review(folder, 1, "SPEAKER_00", "hombre", "alta", "", "anotadora_1")
    assert annotator_answers(folder, 1) == {"SPEAKER_00": "hombre"}  # vale para todos sus cortes


def test_every_session_page_has_the_same_sections(tmp_path, monkeypatch):
    import re

    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("DATA_DIR", str(tmp_path))  # sin datos reales: sesiones sintéticas
    app = Path(__file__).parent.parent / "dashboard" / "app.py"
    layouts = {}
    for s in load_sessions(tmp_path):
        at = AppTest.from_file(str(app), default_timeout=120).run()
        at.selectbox[0].set_value(s.session_id).run()
        titles = [t.value for t in at.title] + [h.value for h in at.header]
        layouts[s.session_id] = [re.sub(r"\(\d+ voces.*\)|Sesión .*", "X", t) for t in titles]
    assert len({tuple(v) for v in layouts.values()}) == 1, layouts


def test_subtitles_are_webvtt_with_speaker_names_and_clip_offset():
    from contracts import AnalysisEvent, AnalysisTimeline, Speaker
    from dashboard.data import Session, subtitles_vtt

    def ev(i, start, end, spk, text):
        return AnalysisEvent(
            event_id=f"e{i}", type="speech", start_s=start, end_s=end, speaker_id=spk,
            text=text, provenance="ai_inferred",
        )  # fmt: skip

    tl = AnalysisTimeline(
        video_id="V", duration_s=100,
        speakers=[Speaker(speaker_id="SPEAKER_00"), Speaker(speaker_id="SPEAKER_01")],
        events=[
            ev(0, 10, 14, "SPEAKER_00", "Buenos días a todas y a todos, empezamos la sesión."),
            ev(1, 14, 20, "SPEAKER_01", "Gracias presidenta."),
        ],
    )  # fmt: skip
    s = Session("V", tl)
    full = subtitles_vtt(s)
    assert full.startswith("WEBVTT\n\n00:00:10.000 --> ")
    assert "Persona 1:" in full and "Persona 2:" in full
    assert all(len(line) <= 42 for line in full.splitlines() if "-->" not in line)
    clip = subtitles_vtt(s, 12.0, 18.0)  # el clip empieza en 0: tiempos desplazados
    assert clip.splitlines()[2].startswith("00:00:00.000 -->")
    assert "Gracias presidenta." in clip and "00:01:" not in clip


def test_summary_includes_the_camera_reading_only_when_there_is_video():
    from dashboard.data import _video_reading

    assert _video_reading(None) == ""
    text = _video_reading(
        {"tiempo_en_pantalla_por_genero_%": {"mujer": 23.1, "hombre": 33.6, "desconocido": 43.3},
         "personas_visibles_max": 4}
    )  # fmt: skip
    assert "mujeres el 23.1 %" in text and "hasta 4 personas" in text and "no quién hay" in text


def test_evolution_reading_compares_only_control_sessions_with_code_numbers():
    from dashboard.data import Session, evolution_reading
    from metrics.registry import MetricResult

    def sess(sid, fecha, titulo, m02):
        s = Session(sid, None)
        s.source = {"fecha_evento": fecha, "titulo": titulo}
        s.metrics = {
            "M02": MetricResult(
                metric_id="M02", name="M02", is_example=False, value=m02, conclusive=True, sample={}
            )
        }  # fmt: skip
        return s

    lines, others = evolution_reading(
        [
            sess("V7", "2018-09-19", "Pleno, sesión 142, sesión de control", 55.13),
            sess("V5", "2026-09-30", "Pleno, sesión 202, sesión de control", 41.65),
            sess("V4", "2026-10-16", "Diputación Permanente", 22.8),
        ]
    )
    assert lines == [
        "Tiempo de palabra de las mujeres (M02): 55,13 % en 2018, 41,65 % en 2026. "
        "De 2018 a 2026: −13,48 puntos."
    ]
    assert others and others[0].startswith("V4")


def test_session_without_evaluation_use_is_a_demo_without_question_metrics(tmp_path):
    import csv
    import shutil

    from dashboard.data import QUESTION_METRICS, SYNTHETIC_DIR
    from sources.manifest import COLUMNS

    for vid in ("V001", "V002"):
        folder = tmp_path / "processed" / vid
        folder.mkdir(parents=True)
        shutil.copy(SYNTHETIC_DIR / "SINTETICO_equilibrado.timeline.json", folder / "timeline.json")
    with (tmp_path / "manifiesto.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, [c for c in COLUMNS if c != "tipo_sesion"])  # manifiesto anterior
        w.writeheader()
        w.writerow({"video_id": "V001", "uso": "demo"})
        w.writerow({"video_id": "V002", "uso": "evaluacion;demo"})
    demo, control = sorted(load_sessions(tmp_path), key=lambda s: s.session_id)
    assert demo.demo and not control.demo
    assert [s.session_id for s in load_sessions(tmp_path)] == ["V002", "V001"]  # demo al final
    for key in QUESTION_METRICS:
        assert metric_card(demo.metrics[key])["valor"] == "no aplica"
    assert metric_card(demo.metrics["M01"])["valor"] != "no aplica"


def test_session_type_from_manifest_decides_question_metrics(tmp_path):
    import csv
    import shutil

    from dashboard.data import SYNTHETIC_DIR, session_label
    from sources.manifest import COLUMNS

    for vid in ("V001", "V002"):
        folder = tmp_path / "processed" / vid
        folder.mkdir(parents=True)
        shutil.copy(SYNTHETIC_DIR / "SINTETICO_equilibrado.timeline.json", folder / "timeline.json")
    with (tmp_path / "manifiesto.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, COLUMNS)
        w.writeheader()
        w.writerow({"video_id": "V001", "uso": "evaluacion", "tipo_sesion": ""})  # acto
        w.writerow({"video_id": "V002", "uso": "test", "tipo_sesion": "control"})
    by_id = {s.session_id: s for s in load_sessions(tmp_path)}
    assert by_id["V001"].demo and "otro formato" in session_label(by_id["V001"])
    assert not by_id["V002"].demo  # control: métricas de preguntas aunque sea de test


def test_measure_a_with_vacancies_is_used_with_a_warning():
    from metrics.diputadas import Conteo, _control

    avisos: list[str] = []
    ok = _control(Conteo(349, 156, 193, 0, 44.7), 350, "A", avisos)
    assert ok.porcentaje == 44.7 and "349 escaños ocupados" in avisos[0]
    assert _control(Conteo(137, 30, 107, 0, 21.9), 350, "A", []).porcentaje is None  # fuera
