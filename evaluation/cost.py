"""Coste de la API del modelo de lenguaje (p. ej. Qwen vía OVH AI Endpoints, compatible con OpenAI).

Los precios NO están en el código: se leen de variables de entorno, que se rellenan a mano desde el
tarifario oficial del proveedor el día de la medición, y se anota la fecha. Sin precios, el informe
da solo los tokens (que es lo que de verdad se mide) y avisa de que falta el precio.

  LLM_PRICE_IN_PER_MTOK    precio por millón de tokens de ENTRADA
  LLM_PRICE_OUT_PER_MTOK   precio por millón de tokens de SALIDA
  LLM_PRICE_CURRENCY       moneda (por defecto EUR)
  LLM_PRICE_DATE           fecha del tarifario consultado (AAAA-MM-DD)

Los motores locales (RulesEngine, un modelo en nuestra propia GPU) no facturan tokens: su coste es
de cómputo (horas de GPU), que se registra aparte (`data/smoke.json` y tiempos de ejecución).
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Prices:
    in_per_mtok: float
    out_per_mtok: float
    currency: str = "EUR"
    date: str = ""

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Prices | None:
        env = os.environ if env is None else env
        try:
            return cls(
                float(env["LLM_PRICE_IN_PER_MTOK"]),
                float(env["LLM_PRICE_OUT_PER_MTOK"]),
                env.get("LLM_PRICE_CURRENCY") or "EUR",
                env.get("LLM_PRICE_DATE", ""),
            )
        except (KeyError, ValueError):
            return None


def cost(tokens_in: int, tokens_out: int, prices: Prices) -> float:
    return (tokens_in * prices.in_per_mtok + tokens_out * prices.out_per_mtok) / 1_000_000


def usage_report(
    decisions: Sequence, prices: Prices | None = None, turns_per_session: int | None = None
) -> dict:
    """Tokens y coste de una lista de `Decision`; proyecta a sesiones si se da `turns_per_session`.

    Los motores sin API (tokens `None`) cuentan 0 y salen como «sin_api».
    """
    billed = [d for d in decisions if d.tokens_in is not None or d.tokens_out is not None]
    t_in = sum(d.tokens_in or 0 for d in billed)
    t_out = sum(d.tokens_out or 0 for d in billed)
    n = len(decisions)
    report: dict = {
        "llamadas_con_api": len(billed),
        "sin_api": n - len(billed),
        "tokens_in": t_in,
        "tokens_out": t_out,
        "tokens_por_turno": round((t_in + t_out) / n, 1) if n else 0.0,
    }
    if prices is None:
        report["aviso"] = "faltan los precios (LLM_PRICE_*): solo se informan los tokens"
        return report
    total = cost(t_in, t_out, prices)
    report.update(
        moneda=prices.currency,
        fecha_tarifario=prices.date,
        coste_total=round(total, 6),
        coste_por_turno=round(total / n, 8) if n else 0.0,
    )
    if turns_per_session and n:
        report["coste_por_sesion_estimado"] = round(total / n * turns_per_session, 4)
    return report


def project(
    tokens_per_turn_in: float,
    tokens_per_turn_out: float,
    turns_per_session: int,
    sessions: int,
    prices: Prices,
) -> dict:
    """Coste previsto para `sessions` sesiones con `turns_per_session` llamadas cada una."""
    per_turn = cost(tokens_per_turn_in, tokens_per_turn_out, prices)
    return {
        "moneda": prices.currency,
        "por_sesion": round(per_turn * turns_per_session, 4),
        "total": round(per_turn * turns_per_session * sessions, 4),
        "llamadas": turns_per_session * sessions,
    }
