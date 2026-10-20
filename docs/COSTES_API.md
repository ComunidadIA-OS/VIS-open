# Evaluación de los costes de la API

El modelo de lenguaje (Qwen, vía OVH AI Endpoints o un servidor propio compatible con OpenAI) es lo único del proyecto que puede facturar por uso. Se evalúa su coste igual que su calidad: **un motor solo se adopta si su mejora de calidad compensa su coste**. Código: `evaluation/cost.py`; el benchmark (`evaluation/benchmark.py`) ya imprime tokens y coste junto al F1.

## Qué se mide

| Qué | Cómo | Dónde sale |
|---|---|---|
| Tokens de entrada y salida por llamada | Campo `usage` de la respuesta de la API (`prompt_tokens`, `completion_tokens`); se anotan también las respuestas descartadas, porque se facturan igual | `Decision.tokens_in` y `tokens_out` |
| Tokens por turno, coste por turno y coste por sesión | `usage_report(decisions, prices, turns_per_session)` | campo `coste` de cada motor en el benchmark |
| Previsión para N sesiones | `project(tokens_in, tokens_out, turnos_por_sesion, sesiones, prices)` | a mano o en un cuaderno |
| Latencia por llamada | `Decision.latency_s` | benchmark |
| Coste de los motores locales | No facturan tokens; su coste es cómputo (horas de GPU) | `data/smoke.json` y tiempos de ejecución en OVH |

## Precios: no están en el código

Los precios cambian y no los inventamos. Se rellenan en el `.env` desde el tarifario oficial del proveedor **el día de la medición**, anotando la fecha:

```
LLM_PRICE_IN_PER_MTOK=      # precio por millón de tokens de entrada
LLM_PRICE_OUT_PER_MTOK=     # precio por millón de tokens de salida
LLM_PRICE_CURRENCY=EUR
LLM_PRICE_DATE=             # AAAA-MM-DD del tarifario consultado
```

Sin precios, el informe da solo los tokens y avisa de que faltan.

### Modelos candidatos en OVH AI Endpoints (catálogo público, consultado el 2026-10-20)

URL de la API (compatible con OpenAI): `https://oai.endpoints.kepler.ai.cloud.ovh.net/v1`. El identificador exacto de cada modelo se obtiene con `python -m decision.llm_check` (lista `GET /models`). Precios por millón de tokens (entrada / salida); **hay que volver a comprobarlos el día de la medición**:

| Modelo | Entrada | Salida | Licencia |
|---|---|---|---|
| Qwen3.5-9B | 0,1 € | 0,15 € | Apache 2.0 |
| Qwen3.6-27B / Qwen3.8-27B | 0,4 € | 2,7 € | Apache 2.0 |
| Qwen3.5-397B-A17B | 0,6 € | 3,6 € | Apache 2.0 |
| gpt-oss-120b | 0,08 € | 0,4 € | Apache 2.0 |

Los modelos Qwen son Apache 2.0, compatibles con nuestra licencia. El más barato que alcance la calidad pedida en el benchmark es el que se elige.

### Comprobar la conexión

```bash
python -m decision.llm_check        # lista modelos; con LLM_MODEL puesto, hace 1 llamada de prueba sintética
```

La clave se lee del `.env` y no se imprime.

## Cómo se evalúa (con los 150 turnos anotados)

```bash
python -m evaluation.benchmark turnos.csv --engines rules,llm --out resultados.json
```

Por cada motor se obtiene la tabla de decisión:

| Motor | F1 macro | % a revisión | Latencia media | Tokens por turno | Coste por sesión |
|---|---|---|---|---|---|
| `rules` (por defecto) | … | … | ~0 | 0 (sin API) | 0 |
| `llm` (Qwen vía API) | … | … | … | … | … |

Regla de decisión (ampliación de `SKILLS.md` §5): se adopta `llm` solo si **gana en F1** o queda a ≤ 2 puntos y reduce el trabajo de revisión humana, **y** su coste por sesión es asumible. Si no, se mantiene `rules`.

## Previsión de la entrega

Con el coste por turno medido, `project(...)` estima el total: 3 sesiones × turnos por sesión × coste por turno, más las llamadas de M09 (preguntas recibidas) y las del benchmark. Conviene presentar el resultado como «coste por sesión» y «coste por 100 sesiones», porque es lo que importa a otras instituciones.

## Otros costes a declarar

- **Cómputo en OVH:** horas de GPU de la transcripción y la separación de voces (de `data/smoke.json` y de los tiempos de ejecución) y del ajuste ligero de Qwen del 28 oct.
- **Almacenamiento:** vídeos originales y salidas; los vídeos no se suben al repositorio.
- **Coste cero a propósito:** el género por pistas del lenguaje, las métricas, la seudonimización y el panel corren en local sin facturación por uso.

## Para la presentación

> **Costes**
> - Lo único que factura por uso es el modelo de lenguaje (Qwen vía API compatible con OpenAI). Medimos tokens por turno y coste por sesión, con precios del tarifario del día anotado.
> - Comparamos coste frente a calidad: el motor de reglas (coste 0) frente al modelo; el modelo solo entra si mejora de forma que compensa.
> - El sistema es agnóstico al modelo: se puede cambiar a uno abierto en nuestro hardware, y el coste pasa a ser de cómputo.
> - Resultado: *se rellena con el benchmark real (27–28 oct)*.

## Límites

- Con datos sintéticos solo se prueba la mecánica; el coste real sale de los 150 turnos reales.
- Si la API no devuelve el campo `usage`, los tokens quedan sin medir (`None`) y el informe lo muestra como «sin_api»; en ese caso hay que estimarlos a mano.
