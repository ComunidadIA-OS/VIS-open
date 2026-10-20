"""Evaluación del vídeo con anotaciones SINTÉTICAS hechas a mano."""

import json

import pytest

from evaluation.video_eval import (
    evaluate_counts,
    evaluate_hands,
    evaluate_track_genders,
    main,
)


def test_counts_bias_detects_undercounting():
    pred = [[0.0, 2], [1.0, 1], [2.0, 3]]
    gold = [(0.0, 3), (1.0, 3), (2.0, 3)]
    r = evaluate_counts(pred, gold)
    assert r["n"] == 3 and r["mae"] == pytest.approx(1.0) and r["bias"] == pytest.approx(-1.0)
    assert r["exact_%"] == pytest.approx(33.3) and r["recall"] == pytest.approx(6 / 9, abs=1e-3)
    assert r["precision"] == 1.0  # nunca cuenta de más


def test_counts_ignores_gold_without_nearby_frame_and_empty():
    assert evaluate_counts([[0.0, 1]], [(10.0, 1)]) == {"n": 0}
    assert evaluate_counts([], [(0.0, 1)]) == {"n": 0}


def test_hands_match_by_time_overlap_and_zone():
    gold = [
        {"zona": "Z2", "inicio_s": 10, "fin_s": 14},
        {"zona": "Z3", "inicio_s": 20, "fin_s": 22},
    ]
    pred = [
        {"zona": "Z2", "inicio_s": 10.5, "fin_s": 14},  # acierto
        {"zona": "Z1", "inicio_s": 20, "fin_s": 22},  # zona distinta: falso positivo
        {"zona": "Z4", "inicio_s": 50, "fin_s": 52},  # falso positivo
    ]
    r = evaluate_hands(pred, gold)
    assert (r["aciertos"], r["anotadas"], r["detectadas"]) == (1, 2, 3)
    assert r["precision"] == pytest.approx(1 / 3, abs=1e-3) and r["recall"] == 0.5
    assert evaluate_hands(pred, gold, same_zone=False)["aciertos"] == 2


def test_track_gender_reports_unknown_apart_and_who_is_left_unlabelled():
    gold = {1: "mujer", 2: "mujer", 3: "hombre", 4: "hombre", 5: "mujer"}
    pred = {1: "mujer", 2: "desconocido", 3: "hombre", 4: "hombre", 5: "desconocido"}
    r = evaluate_track_genders(pred, gold)
    assert r["etiquetadas_%"] == 60.0 and r["acierto_sobre_etiquetadas_%"] == 100.0
    assert r["sin_etiquetar_por_genero"] == {"mujer": "2 de 3", "hombre": "0 de 2"}


def test_cli_end_to_end(tmp_path, capsys):
    video = {
        "personas_por_fotograma": [[0.0, 1], [1.0, 2]],
        "manos_levantadas": [{"zona": "Z1", "inicio_s": 0, "fin_s": 2}],
        "pistas": [{"pista": 1, "genero_por_audio": "mujer"}],
    }
    (tmp_path / "v.json").write_text(json.dumps(video), encoding="utf-8")
    (tmp_path / "p.csv").write_text("t_s,n_personas\n0,1\n1,2\n", encoding="utf-8")
    (tmp_path / "m.csv").write_text("zona,inicio_s,fin_s\nZ1,0,2\n", encoding="utf-8")
    (tmp_path / "t.csv").write_text("pista,genero\n1,mujer\n", encoding="utf-8")
    main(
        [
            str(tmp_path / "v.json"),
            "--personas", str(tmp_path / "p.csv"),
            "--manos", str(tmp_path / "m.csv"),
            "--pistas", str(tmp_path / "t.csv"),
        ]
    )  # fmt: skip
    out = json.loads(capsys.readouterr().out)
    assert out["personas"]["mae"] == 0 and out["manos"]["f1"] == 1.0
    assert out["genero_pistas"]["acierto_sobre_etiquetadas_%"] == 100.0
