"""Informe de análisis: tokens y precio calculados a mano."""

from evaluation.cost import Prices
from evaluation.informe import build_report, cost_section


def write_detail(path):
    path.parent.mkdir(parents=True)
    path.write_text(
        "turn_id,tokens_in,tokens_out,latencia_s\na,400,60,2.0\nb,600,40,4.0\n", encoding="utf-8"
    )


def test_cost_section_with_prices(tmp_path):
    detail = tmp_path / "d" / "detalle_llm.csv"
    write_detail(detail)
    text = "\n".join(cost_section(detail, Prices(0.1, 0.15, "EUR", "2026-10-20")))
    # 1000 tokens de entrada y 100 de salida: (1000*0.1 + 100*0.15)/1e6 = 0.000115 EUR
    assert "1000 / 500" in text and "100 / 50" in text and "0.000115 EUR" in text
    assert "3.00 s" in text


def test_cost_section_without_prices_or_file(tmp_path):
    detail = tmp_path / "d" / "detalle_llm.csv"
    assert "aún no se ha medido" in cost_section(detail, None)[-1]
    write_detail(detail)
    assert "faltan `LLM_PRICE_*`" in "\n".join(cost_section(detail, None))


def test_report_without_sessions_still_builds(tmp_path):
    text = build_report(tmp_path, None)
    assert "Análisis de audio" in text and "Análisis de vídeo" in text and "Consumo" in text
