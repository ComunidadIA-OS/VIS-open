# Marco de métricas

Código en `metrics/`. **No incluye M01 a M13 ni sus umbrales**: son de Ivette y siguen pendientes de su libro de códigos. Aquí solo está lo común para que ella añada las suyas.

## Qué hay

| Pieza | Fichero | Para qué |
|---|---|---|
| `timeline_to_frame` | `metrics/frame.py` | Pasa un `AnalysisTimeline` a un DataFrame (una fila por evento, con el género de la voz o `sin_atribuir`). |
| `speech_time_by_speaker`, `speech_time_by_gender` | `metrics/frame.py` | Tiempo de palabra por voz y por género. `desconocido` (voz) y `sin_atribuir` (evento sin voz) salen **aparte**, nunca repartidos entre mujer y hombre. |
| `sample_of` | `metrics/frame.py` | Tamaño de muestra: eventos, voces, voces con género conocido, segundos, parte sin atribuir. |
| `@metric`, `run_metric`, `MetricResult` | `metrics/registry.py` | Registro de métricas y resultado con la regla de «no concluyente». |
| `gap_is_conclusive` | `metrics/registry.py` | Regla 5 de CLAUDE.md para una brecha (umbral, parte sin atribuir, margen). El **umbral es obligatorio y sin valor por defecto**: lo fija Ivette. |
| `X00_EJEMPLO` | `metrics/example.py` | Métrica de ejemplo, marcada `is_example=True`. Sin validez. |

## Regla de «no concluyente»

`run_metric` calcula antes la muestra. Si hay menos voces con género conocido o menos segundos con género conocido que los mínimos de la métrica, devuelve `conclusive=False`, `value=None` y el motivo («no concluyente: muestra insuficiente (…)»). Todo resultado lleva su `sample`, y la procedencia es `computed`: las cifras las calcula pandas, nunca un LLM.

## Cómo añadir una métrica (Ivette)

1. Define la métrica en `docs/metricas.md` (ID Mxx, fórmula, umbral, limitaciones).
2. Copia `metrics/example.py` a `metrics/mxx.py`: cambia `metric_id`, `name`, la docstring y el cálculo. Fija **tú** `min_speakers_known_gender` y `min_known_gender_seconds` (no tienen valor por defecto).
3. Devuelve `MetricOutput(value=..., margin=...)`; si comparas grupos, usa `gap_is_conclusive` con tu umbral.
4. Importa el módulo en `metrics/__init__.py` para que se registre.
5. Tests con un caso hecho a mano y un caso límite (un solo grupo, sin datos), como en `tests/test_metrics_framework.py`.

## Ejemplo de uso

```python
from contracts import AnalysisTimeline
from metrics import run_metric, timeline_to_frame

tl = AnalysisTimeline.model_validate_json(open("timeline.json", encoding="utf-8").read())
result = run_metric("X00_EJEMPLO", timeline_to_frame(tl))
print(result.conclusive, result.value, result.reason, result.sample)
```

## Límites

- Suma duraciones de eventos; no resta solapes entre voces distintas.
- El margen de error lo calcula cada métrica; el marco no impone ninguno.
