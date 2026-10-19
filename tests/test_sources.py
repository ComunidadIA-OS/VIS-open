import csv
import json
from pathlib import Path

import pytest

from pipeline import run as run_mod
from sources import (
    CongresoSource,
    DownloadDisabled,
    ManifestError,
    check_row,
    parse_session_url,
    require_ready,
    sha256_file,
)
from sources.manifest import COLUMNS, append_row

URL = (
    "https://app.congreso.es/AudiovisualCongreso/audiovisualdetalledisponible"
    "?codOrgano=70&codSesion=12&idLegislaturaElegida=15&fechaSesion=21/05/2025"
)
TEMPLATE = Path(__file__).parent.parent / "docs" / "manifiesto-plantilla.csv"


def complete_row(video: Path, **over: str) -> dict[str, str]:
    row = CongresoSource().manifest_row(
        URL,
        video,
        descargado_por="Veru",
        licencia_verificada="si",
        tramo_inicio="00:00:00",
        tramo_fin="00:00:10",
        duracion_s="10",
        fecha_descarga="2026-10-17",
        ruta_drive="02_originales/x.mp4",
        fecha_borrado="2026-12-04",
    )
    row.update(over)
    return row


@pytest.fixture
def video(tmp_path: Path) -> Path:
    path = tmp_path / "V001.mp4"
    path.write_bytes("no es un vídeo real, solo bytes sintéticos".encode())
    return path


def test_columns_match_template():
    header = next(csv.reader(TEMPLATE.open(encoding="utf-8")))
    assert header == COLUMNS


def test_parse_url():
    ref = parse_session_url(URL)
    assert (ref.cod_organo, ref.cod_sesion, ref.legislatura) == ("70", "12", "15")
    assert ref.event_date == "2025-05-21"


@pytest.mark.parametrize(
    "bad",
    [
        "https://evil.example/AudiovisualCongreso/x?codOrgano=1&codSesion=1"
        "&idLegislaturaElegida=1&fechaSesion=01/01/2025",
        "https://app.congreso.es/AudiovisualCongreso/x?codOrgano=1",
        "ftp://app.congreso.es/x",
    ],
)
def test_parse_url_rejects_other_hosts_and_missing_params(bad):
    with pytest.raises(ValueError):
        parse_session_url(bad)


def test_unknown_date_format_is_left_empty():
    ref = parse_session_url(URL.replace("21/05/2025", "ayer"))
    assert ref.event_date == ""


def test_manifest_row_fills_hash_and_never_alters_file(video):
    before = video.read_bytes()
    row = CongresoSource().manifest_row(URL, video)
    assert row["sha256"] == sha256_file(video) and row["video_id"] == "V001"
    assert row["uso_entrenamiento"] == "no" and row["licencia_verificada"] == "pendiente"
    assert video.read_bytes() == before


def test_incomplete_row_lists_what_is_missing(video):
    row = CongresoSource().manifest_row(URL, video)
    problems = check_row(row)
    assert any("descargado_por" in p for p in problems)
    assert any("licencia_verificada debe ser 'si'" in p for p in problems)


def test_complete_row_passes(video):
    assert check_row(complete_row(video)) == []


def test_template_example_row_is_rejected():
    with TEMPLATE.open(encoding="utf-8") as fh:
        example = next(csv.DictReader(fh))
    assert any("ejemplo" in p for p in check_row(example))


def test_training_use_is_always_no(video):
    problems = check_row(complete_row(video, uso_entrenamiento="si"))
    assert any("uso_entrenamiento" in p for p in problems)


def test_require_ready_refuses_missing_row_and_explains(video, tmp_path):
    manifest = tmp_path / "m.csv"
    append_row(complete_row(video, video_id="OTRO"), manifest)
    with pytest.raises(ManifestError, match="no tiene fila"):
        require_ready(video, manifest)


def test_require_ready_refuses_incomplete_row(video, tmp_path):
    manifest = tmp_path / "m.csv"
    append_row(CongresoSource().manifest_row(URL, video), manifest)
    with pytest.raises(ManifestError, match="descargado_por"):
        require_ready(video, manifest)


def test_require_ready_detects_altered_video(video, tmp_path):
    manifest = tmp_path / "m.csv"
    append_row(complete_row(video), manifest)
    assert require_ready(video, manifest)["video_id"] == "V001"
    video.write_bytes(b"alterado")
    with pytest.raises(ManifestError, match="sha256"):
        require_ready(video, manifest)


def test_run_refuses_unlisted_video_before_any_processing(video, tmp_path):
    with pytest.raises(SystemExit, match="no existe el manifiesto"):
        run_mod.main([str(video), "--manifest", str(tmp_path / "nope.csv")])


def test_source_citation_has_source_and_date(video):
    cited = run_mod.source_citation(complete_row(video))
    assert "Congreso de los Diputados" in cited["cita"]
    assert "2025-05-21" in cited["cita"] and "2026-10-17" in cited["cita"]
    json.dumps(cited)


def test_download_is_disabled_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("AUTO_DOWNLOAD", raising=False)
    with pytest.raises(DownloadDisabled, match="AUTO_DOWNLOAD=false"):
        CongresoSource().download(URL, tmp_path)


def test_download_has_no_network_even_if_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTO_DOWNLOAD", "true")
    with pytest.raises(DownloadDisabled, match="sin implementar"):
        CongresoSource().download(URL, tmp_path)
