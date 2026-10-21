"""Partes puras del script de ajuste (sin GPU ni modelo): datos, parseo y métricas."""

import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / "finetune" / "train_lora.py"


@pytest.fixture(scope="module")
def tl():
    import importlib.util

    spec = importlib.util.spec_from_file_location("train_lora", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # no importa torch ni transformers hasta que hace falta
    return module


def test_smoke_examples_are_balanced_closed_json(tl):
    rows = tl.smoke_examples()
    assert len(rows) == 16
    answers = [json.loads(r["messages"][2]["content"]) for r in rows]
    assert sum(a["is_question"] for a in answers) == 8
    assert all(a["evidence"] is None for a in answers if not a["is_question"])
    for r in rows:
        assert [m["role"] for m in r["messages"]] == ["system", "user", "assistant"]


def test_read_jsonl_validates_roles(tl, tmp_path):
    good = tmp_path / "g.jsonl"
    good.write_text("\n".join(json.dumps(r) for r in tl.smoke_examples()[:2]), encoding="utf-8")
    assert len(tl.read_jsonl(good)) == 2
    bad = tmp_path / "b.jsonl"
    bad.write_text(json.dumps({"messages": [{"role": "user", "content": "x"}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="system, user y assistant"):
        tl.read_jsonl(bad)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('{"is_question": true, "confidence": 1}', True),
        ('Claro: {"is_question": false}', False),
        ('{"is_question": "sí"}', None),
        ("no es json", None),
        ("{roto", None),
    ],
)
def test_parse_answer(tl, text, expected):
    assert tl.parse_answer(text) is expected


def test_prf1_by_hand(tl):
    r = tl.prf1([True, True, False, False], [True, False, True, False])
    assert r == {"precision": 0.5, "recall": 0.5, "f1": 0.5}
    assert tl.prf1([False], [False]) == {"precision": 0.0, "recall": 0.0, "f1": 0.0}
