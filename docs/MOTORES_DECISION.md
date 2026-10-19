# Motores de decisión y benchmark

Código en `decision/engine.py`, `decision/llm_engine.py` y `evaluation/benchmark.py`. Esta rama parte de `genero-lenguaje` (el `RulesEngine` usa sus pistas).

## Motores

| Motor | Qué hace | Cuándo |
|---|---|---|
| `RulesEngine` (por defecto) | Aplica las pistas de `decision/cues/<idioma>.toml` al turno y a lo dicho justo antes | Siempre disponible, sin red |
| `LLMEngine` | Pregunta a un servidor compatible con OpenAI (`LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` opcional del `.env`) | Si gana el benchmark o queda a ≤ 2 puntos de F1 (SKILLS.md §5) |

Elegir: `DECISION_ENGINE=rules|llm` o `get_engine("llm")`. Laya, nimble o Kev se usan poniéndolos en `LLM_MODEL`. **`nimble-v3` se rechaza** (CC BY-NC); `LLM_MODEL` vacío también.

Todos devuelven `Decision`: `gender` (`mujer`/`hombre`/`desconocido`), `confidence`, `evidence`, `reason`, `engine`, `error`, `latency_s`. Confianza < 0,7 o `error` → `needs_review`. Un fallo del motor (red, formato) nunca rompe el proceso: la voz queda `desconocido` y va a revisión.

## Defensa ante inyección de prompt (LLMEngine)

- La transcripción va entre `<DATOS-código>…</DATOS-código>` con un código aleatorio distinto en cada llamada; las instrucciones (rol `system`) la declaran dato y nunca la mezclan.
- Sin `tools` ni `tool_choice`: el modelo solo puede responder.
- Salida cerrada: `response_format` con el esquema JSON (`additionalProperties: false`) y segunda validación con Pydantic. Fuera de esquema → `desconocido` + error.
- Una respuesta con género solo vale si su `evidence` es una **cita literal** del turno o del contexto; si no, se descarta (cubre un modelo que "obedece" una orden escondida).
- Test con una transcripción hostil: `tests/test_decision_engines.py`.
- **Límite:** una pista lingüística escrita dentro del texto («soy la diputada») cuenta como pista, también para el `RulesEngine`; la revisión humana y la procedencia (`ai_inferred`) existen por eso. Pendiente: probar los 10 turnos maliciosos de SKILLS.md §6 contra un modelo real.

## Benchmark

```bash
python -m evaluation.benchmark turnos.csv --engines rules,llm --out resultados.json
```

CSV UTF-8, una fila por turno:

| Columna | Obligatoria | Contenido |
|---|---|---|
| `turn_id` | sí | Identificador único |
| `text` | sí | Texto del turno |
| `context_before` | no | Lo dicho justo antes (p. ej. la Presidencia dando la palabra) |
| `label` | sí | `mujer`, `hombre` o `desconocido` (etiqueta de las anotadoras) |

Salida por motor: F1, precisión y recall por clase, F1 macro, exactitud, matriz de confusión, porcentaje que va a revisión, errores y latencia media. Valida las etiquetas y los `turn_id` repetidos.

Los datos sintéticos solo prueban la mecánica. Los 150 turnos reales (30 ambiguos → `desconocido`) los anotan Ivette y Veru; **no se suben al repo**. Pendiente: matriz por orden de opciones, sesgo por nombre/género declarado y calibración (SKILLS.md §5).
