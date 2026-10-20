"""Coste de la API con tokens y precios SINTÉTICOS (no son precios reales de nadie)."""

import json

import pytest

from decision.engine import Decision, RulesEngine, Turn
from decision.llm_engine import LLMEngine
from evaluation.benchmark import evaluate
from evaluation.cost import Prices, cost, project, usage_report

PRICES = Prices(in_per_mtok=1.0, out_per_mtok=3.0, currency="EUR", date="2026-10-20")  # sintéticos


def test_cost_formula():
    assert cost(1_000_000, 0, PRICES) == 1.0
    assert cost(0, 1_000_000, PRICES) == 3.0
    assert cost(500, 100, PRICES) == pytest.approx((500 * 1 + 100 * 3) / 1e6)


def test_prices_from_env_only_when_both_are_numbers():
    assert Prices.from_env({}) is None
    assert Prices.from_env({"LLM_PRICE_IN_PER_MTOK": "x", "LLM_PRICE_OUT_PER_MTOK": "1"}) is None
    p = Prices.from_env(
        {"LLM_PRICE_IN_PER_MTOK": "0.5", "LLM_PRICE_OUT_PER_MTOK": "1.5", "LLM_PRICE_DATE": "d"}
    )
    assert p == Prices(0.5, 1.5, "EUR", "d")


def test_usage_report_with_and_without_prices():
    ds = [Decision(tokens_in=1000, tokens_out=100), Decision(tokens_in=2000, tokens_out=200)]
    ds.append(Decision())  # un motor sin API cuenta como «sin_api»
    r = usage_report(ds, PRICES, turns_per_session=50)
    assert (r["llamadas_con_api"], r["sin_api"], r["tokens_in"], r["tokens_out"]) == (
        2,
        1,
        3000,
        300,
    )
    assert r["coste_total"] == pytest.approx((3000 + 900) / 1e6)
    assert r["coste_por_sesion_estimado"] == pytest.approx(r["coste_total"] / 3 * 50, abs=1e-4)
    assert "aviso" in usage_report(ds, None) and "coste_total" not in usage_report(ds, None)


def test_project():
    p = project(1000, 100, turns_per_session=100, sessions=3, prices=PRICES)
    assert p["llamadas"] == 300 and p["total"] == pytest.approx(3 * p["por_sesion"], abs=1e-3)


def test_llm_engine_records_tokens_from_usage_even_when_rejected():
    reply = {
        "choices": [{"message": {"content": json.dumps({"gender": "mujer", "confidence": 1.0})}}],
        "usage": {"prompt_tokens": 321, "completion_tokens": 12},
    }  # sin evidencia literal: se descarta, pero los tokens se facturan igual
    engine = LLMEngine("http://x/v1", "qwen3", transport=lambda *a: reply)
    d = engine.decide(Turn(turn_id="1", text="hola"))
    assert d.error and (d.tokens_in, d.tokens_out) == (321, 12)


def test_llm_engine_without_usage_field_does_not_break():
    reply = {"choices": [{"message": {"content": '{"gender":"desconocido","confidence":0.1}'}}]}
    d = LLMEngine("http://x/v1", "qwen3", transport=lambda *a: reply).decide(
        Turn(turn_id="1", text="hola")
    )
    assert d.tokens_in is None and d.error is None


def test_benchmark_reports_cost_next_to_quality(monkeypatch):
    monkeypatch.setenv("LLM_PRICE_IN_PER_MTOK", "1")
    monkeypatch.setenv("LLM_PRICE_OUT_PER_MTOK", "3")
    rules = evaluate(RulesEngine(), [(Turn(turn_id="1", text="Hola."), "desconocido")])
    assert rules["coste"]["sin_api"] == 1 and rules["coste"]["coste_total"] == 0
