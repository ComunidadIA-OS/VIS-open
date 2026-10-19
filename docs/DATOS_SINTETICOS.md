# Datos sintéticos de ejemplo

**Todo es inventado.** Ninguna persona, voz ni transcripción real. Sirven para que Veru monte el panel y para que Ivette pruebe sus métricas sin esperar a los datos reales. Código: `evaluation/synthetic/generator.py`. Semilla fija (42): mismos datos siempre.

```bash
make synthetic        # o: python -m evaluation.synthetic [--out DIR] [--seed N]
```

Ya están generados en `evaluation/synthetic/muestras/` (un test comprueba que coinciden con el generador). Marcado: todos los ficheros empiezan por `SINTETICO`, todas las tablas llevan `origen=SINTETICO`, y `video_id` y `source` de las líneas de tiempo empiezan por `SINTETICO`.

## Escenarios (uno por línea de tiempo)

| `video_id` | Qué contiene |
|---|---|
| `SINTETICO_equilibrado` | 2 mujeres y 2 hombres con tiempo parecido |
| `SINTETICO_pocas_mujeres` | 1 mujer y 4 hombres (brecha grande) |
| `SINTETICO_con_desconocidos` | 2 voces de género `desconocido` y 15 % de intervenciones **sin voz atribuida** |
| `SINTETICO_muestra_insuficiente` | 3 turnos y una sola voz con género conocido: caso «no concluyente» |
| `SINTETICO_con_manos` | Como el equilibrado, más 12 eventos `hand_raise` (zona, `granted` sí/no) |

La Presidencia es `SPEAKER_00` y da la palabra antes de cada turno («Tiene la palabra la señora diputada»). Algunos turnos incluyen una concordancia propia («Estoy muy agradecida…»). Las confianzas van de 0,55 a 0,98, así que hay eventos con `needs_review`.

## Ficheros

| Fichero | Una fila por… | Para quién |
|---|---|---|
| `SINTETICO_<escenario>.timeline.json` | `AnalysisTimeline` completa (contrato de `contracts/`) | Ivette (métricas), Veru |
| `SINTETICO_eventos.csv` | evento | Veru (panel) |
| `SINTETICO_resumen_genero.csv` | línea de tiempo | Veru (tarjetas, gráfico) |
| `SINTETICO_turnos.csv` | turno con contexto y etiqueta | benchmark de motores (rama `decision-motores`) |
| `SINTETICO_revision.csv` | voz (formato `ReviewRow`) | prueba del flujo de revisión |

### `SINTETICO_eventos.csv`
`origen, video_id, event_id, type (speech|hand_raise), start_s, end_s, duration_s, speaker_id (vacío si no hay voz), gender (mujer|hombre|desconocido|sin_atribuir), gender_source, provenance, confidence, zone_id, granted (true|false), text`.
`sin_atribuir` = evento sin voz; `desconocido` = voz con género desconocido. Se muestran siempre por separado.

### `SINTETICO_resumen_genero.csv`
`origen, video_id, n_speech_events, n_voices, n_voices_known_gender, seconds_mujer, seconds_hombre, seconds_desconocido, seconds_sin_atribuir, share_mujer_sobre_conocido (0 a 100; vacío si no hay género conocido), unattributed_share (0 a 1: desconocido + sin_atribuir sobre el total), conclusivo_ejemplo`.
`conclusivo_ejemplo` usa una regla **de ejemplo** (≥ 2 voces con género conocido y ≥ 60 s) solo para que el panel enseñe un caso «no concluyente». **No es el criterio de Ivette.**

### `SINTETICO_turnos.csv`
`origen, turn_id, context_before, text, label (mujer|hombre|desconocido)`. Es el formato del benchmark de `docs/MOTORES_DECISION.md` (rama `decision-motores`).

## Ejemplo de uso

```python
import json
import pandas as pd
from contracts import AnalysisTimeline

tl = AnalysisTimeline.model_validate_json(
    open("evaluation/synthetic/muestras/SINTETICO_pocas_mujeres.timeline.json", encoding="utf-8").read()
)
resumen = pd.read_csv("evaluation/synthetic/muestras/SINTETICO_resumen_genero.csv")
print(resumen[["video_id", "share_mujer_sobre_conocido", "unattributed_share", "conclusivo_ejemplo"]])
```

## Límites

Los tiempos y textos son simples: no imitan la riqueza de un debate real (solapes, ruido, errores de diarización). Sirven para probar la mecánica, no para sacar conclusiones.
