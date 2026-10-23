import csv

import pytest

from pipeline import sesion
from sources.manifest import COLUMNS


def _data(tmp_path, ids):
    with (tmp_path / "manifiesto.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, COLUMNS)
        w.writeheader()
        for vid in ids:
            w.writerow({"video_id": vid})
    (tmp_path / "raw").mkdir()
    return tmp_path


def test_pending_are_sessions_with_video_and_no_timeline(tmp_path):
    data = _data(tmp_path, ["V005", "V008", "V009"])
    for vid in ("V005", "V008"):
        (data / "raw" / f"{vid}.mp4").write_bytes(b"x")
    (data / "processed" / "V005").mkdir(parents=True)
    (data / "processed" / "V005" / "timeline.json").write_text("{}")
    assert sesion.pending(data) == ["V008"]  # V005 ya hecha; V009 sin vídeo


def test_steps_in_order_and_engine_from_environment(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(sesion, "require_ready", lambda *a: {})
    monkeypatch.setattr(
        sesion, "_run", lambda *a: calls.append(a[0] if a[0] != "metrics.m09" else a)
    )
    monkeypatch.setenv("LLM_API_KEY", "x")
    monkeypatch.delenv("POSE_MODEL", raising=False)
    sesion.analyze_session("V008", tmp_path)
    assert calls[:2] == ["pipeline.run", "decision.roles"]
    assert calls[2][-2:] == ("--engine", "llm") and len(calls) == 3  # sin POSE_MODEL, sin vídeo
    assert (tmp_path / "processed" / "V008" / "tiempos.json").is_file()


def test_new_videos_are_the_ones_without_a_manifest_row(tmp_path):
    data = _data(tmp_path, ["V005"])
    for vid in ("V005", "V008"):
        (data / "raw" / f"{vid}.mp4").write_bytes(b"x")
    assert [v.stem for v in sesion.new_videos(data)] == ["V008"]


MASTER = """#EXTM3U
#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="aud",NAME="Castellano",LANGUAGE="es",URI="audio_es.m3u8"
#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="aud",NAME="Versión original",URI="audio_vo.m3u8"
#EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=640x360,AUDIO="aud"
v360.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2500000,RESOLUTION=1280x720,AUDIO="aud"
v720.m3u8
"""
BASE = "https://cdn.example/s/master.m3u8"


def test_hls_takes_best_video_and_only_the_original_audio():
    video, audio = sesion.pick_tracks(MASTER, BASE)
    assert video == "https://cdn.example/s/v720.m3u8"
    assert audio == "https://cdn.example/s/audio_vo.m3u8"  # nunca la interpretación


def test_hls_without_original_audio_stops():
    no_original = MASTER.replace('NAME="Versión original"', 'NAME="Inglés"')
    with pytest.raises(sesion.InterpretationOnly):
        sesion.pick_tracks(no_original, BASE)


def test_hls_with_a_single_audio_inside_the_video():
    master = "#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1000\nv.m3u8\n"
    assert sesion.pick_tracks(master, BASE) == ("https://cdn.example/s/v.m3u8", None)


def test_master_url_comes_from_the_session_page_url():
    page = (
        "https://app.congreso.es/AudiovisualCongreso/audiovisualdetalledisponible?codOrgano=400"
        "&codSesion=202&idLegislaturaElegida=15&fechaSesion=30/09/2026"
    )
    assert sesion.master_urls(page)[0] == (
        "https://streaming.congreso.es:8443/vod/ondemand/video/leg15/400/15_000400_202/cortes/"
        "smil:15_000400_202.smil/manifest.m3u8"
    )


def test_manifest_xlsx_has_dropdowns_for_validation(tmp_path):
    import pytest as _pytest

    openpyxl = _pytest.importorskip("openpyxl")
    from evaluation.xlsxio import csv_to_xlsx

    data = _data(tmp_path, ["V008"])
    ws = openpyxl.load_workbook(csv_to_xlsx(data / "manifiesto.csv")).worksheets[0]
    lists = [dv.formula1 for dv in ws.data_validations.dataValidation]
    assert '"si,pendiente"' in lists  # licencia_verificada


def test_permanent_deputation_is_excluded(tmp_path, monkeypatch):
    import pytest as _pytest

    monkeypatch.setenv("DATA_DIR", str(_data(tmp_path, [])))
    other = (
        "https://app.congreso.es/AudiovisualCongreso/audiovisualdetalledisponible?codOrgano=500"
        "&codSesion=8&idLegislaturaElegida=15&fechaSesion=16/10/2026"
    )
    with _pytest.raises(SystemExit, match="Diputación Permanente"):
        sesion.main(["V009", "--congreso-url", other])
