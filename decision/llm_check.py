"""Comprobación de la API del modelo (OVH AI Endpoints u otra compatible con OpenAI).

Uso: python -m decision.llm_check
1. Lista los modelos disponibles (GET /models); con LLM_MODEL vacío, solo eso.
2. Con LLM_MODEL puesto, hace UNA llamada de prueba con un turno SINTÉTICO y muestra la decisión,
   los tokens, la latencia y el coste estimado (si hay precios LLM_PRICE_* en el `.env`).

Lee `.env` (LLM_BASE_URL, LLM_API_KEY, LLM_MODEL...). La clave nunca se imprime.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping

from decision.engine import Turn
from decision.llm_engine import DEFAULT_BASE_URL, LLMEngine
from evaluation.cost import Prices, usage_report
from pipeline.envfile import load_dotenv

Getter = Callable[[str, Mapping[str, str]], dict]


def urllib_get(url: str, headers: Mapping[str, str]) -> dict:
    req = urllib.request.Request(url, headers=dict(headers))
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - URL de la configuración
        return json.loads(resp.read())


def list_models(base_url: str, api_key: str, get: Getter = urllib_get) -> list[str]:
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    data = get(f"{base_url.rstrip('/')}/models", headers)
    return sorted(m["id"] for m in data.get("data", []) if "id" in m)


def main() -> None:
    load_dotenv()
    base = os.environ.get("LLM_BASE_URL") or DEFAULT_BASE_URL
    key = os.environ.get("LLM_API_KEY", "")
    model = os.environ.get("LLM_MODEL", "")
    state = "puesta" if key else "VACÍA"
    print(f"Servidor: {base} | clave: {state} | modelo: {model or '(sin elegir)'}")
    try:
        ids = list_models(base, key)
    except urllib.error.HTTPError as exc:
        msg = f"error {exc.code} al listar modelos: revisa LLM_BASE_URL y LLM_API_KEY"
        raise SystemExit(msg) from None
    except OSError as exc:
        raise SystemExit(f"no se pudo conectar: {type(exc).__name__}") from None
    print(f"{len(ids)} modelos:", ", ".join(ids))
    if not model:
        print("Pon en .env LLM_MODEL=<uno de la lista> y vuelve a ejecutar.")
        return
    engine = LLMEngine.from_env()
    print(
        "parámetros extra:",
        sorted(engine.extra_body) or "ninguno",
        "| max_tokens:",
        engine.max_tokens,
    )
    turn = Turn(
        turn_id="prueba",
        context_before="Tiene la palabra la señora Persona 2.",  # sintético
        text="Gracias, presidenta. Buenos días, señorías.",
    )
    d = engine.decide(turn)
    print("decisión:", d.gender, d.confidence, "| error:", d.error, "| latencia_s:", d.latency_s)
    print("coste:", json.dumps(usage_report([d], Prices.from_env()), ensure_ascii=False))


if __name__ == "__main__":
    main()
