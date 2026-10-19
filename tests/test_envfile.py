import os

from pipeline.envfile import load_dotenv, parse_env


def test_parse_handles_comments_empty_values_and_quotes():
    text = "# c\nHF_TOKEN=   # nota\nA=1  # nota\nB='x y'\n\nsin_igual\nWHISPER_LANGUAGE=\n"
    assert parse_env(text) == {"HF_TOKEN": "", "A": "1", "B": "x y", "WHISPER_LANGUAGE": ""}


def test_load_does_not_override_existing_env(tmp_path, monkeypatch):
    f = tmp_path / ".env"
    f.write_text("VIS_T1=desde_fichero\nVIS_T2=nuevo\n", encoding="utf-8")
    monkeypatch.setenv("VIS_T1", "del_entorno")
    monkeypatch.delenv("VIS_T2", raising=False)
    assert load_dotenv(f) == ["VIS_T2"]
    assert os.environ["VIS_T1"] == "del_entorno" and os.environ["VIS_T2"] == "nuevo"
    monkeypatch.delenv("VIS_T2")


def test_missing_file_is_ignored(tmp_path):
    assert load_dotenv(tmp_path / "no.env") == []
