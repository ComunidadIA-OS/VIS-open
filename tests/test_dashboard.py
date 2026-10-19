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
