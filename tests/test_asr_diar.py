"""WER y DER calculados a mano sobre ejemplos sintéticos."""

import pytest

from evaluation.asr_diar import der, main, read_segments, wer


def test_wer_by_hand():
    r = wer("Buenos días, señorías.", "buenos dias señorías hoy")
    # «días» → «dias» (1 sustitución) + «hoy» (1 inserción) sobre 3 palabras
    assert r["wer"] == pytest.approx(2 / 3, abs=1e-4)
    assert (r["sustituciones"], r["borrados"], r["inserciones"]) == (1, 0, 1)


def test_wer_deletion_and_perfect_and_empty_reference():
    assert wer("a b c d", "a c d")["borrados"] == 1
    assert wer("hola mundo", "Hola, mundo.")["wer"] == 0
    with pytest.raises(ValueError):
        wer("...", "algo")


def test_der_perfect_is_zero_even_with_other_labels():
    ref = [("A", 0, 10), ("B", 10, 20)]
    hyp = [("x", 0, 10), ("y", 10, 20)]
    assert der(ref, hyp)["der"] == 0


def test_der_missed_false_alarm_and_confusion():
    ref = [("A", 0, 10), ("B", 10, 20)]
    # Hipótesis: 0-8 bien (x=A); 8-10 sin voz (2 s perdidos); 10-15 etiquetado x (confusión 5 s);
    # 15-20 bien (y=B); 20-22 falsa alarma de 2 s.
    hyp = [("x", 0, 8), ("x", 10, 15), ("y", 15, 20), ("y", 20, 22)]
    r = der(ref, hyp)
    assert r["voz_perdida"] == pytest.approx(0.1, abs=1e-3)
    assert r["confusion"] == pytest.approx(0.25, abs=1e-3)
    assert r["falsa_alarma"] == pytest.approx(0.1, abs=1e-3)
    assert r["der"] == pytest.approx(0.45, abs=1e-3)


def test_der_overlap_counts_both_speakers():
    ref = [("A", 0, 10), ("B", 5, 10)]  # 15 s de voz (5 solapados)
    hyp = [("x", 0, 10)]  # se pierde B
    r = der(ref, hyp)
    assert r["voz_perdida"] == pytest.approx(5 / 15, abs=1e-3)
    assert r["confusion"] == 0


def test_der_rejects_empty_reference_and_bad_turn():
    with pytest.raises(ValueError):
        der([], [("a", 0, 1)])
    with pytest.raises(ValueError):
        der([("a", 5, 1)], [])


def test_cli_reads_csv_and_text(tmp_path, capsys):
    ref, hyp = tmp_path / "r.csv", tmp_path / "h.csv"
    ref.write_text("speaker_id,start_s,end_s\nA,0,2\n", encoding="utf-8")
    hyp.write_text("speaker_id,start_s,end_s\nz,0,2\n", encoding="utf-8")
    assert read_segments(ref) == [("A", 0.0, 2.0)]
    main(["der", str(ref), str(hyp)])
    assert '"der": 0.0' in capsys.readouterr().out
    t1, t2 = tmp_path / "a.txt", tmp_path / "b.txt"
    t1.write_text("uno dos", encoding="utf-8")
    t2.write_text("uno tres", encoding="utf-8")
    main(["wer", str(t1), str(t2)])
    assert '"wer": 0.5' in capsys.readouterr().out
