# M09 · preguntas recibidas

**Estado (26 oct 2026):** implementada según la definición de Ivette (`docs/metricas.md`), con su decisión del 26 oct (opción 3):

- **En la sesión de control**, cuenta toda pregunta que **anuncia la Presidencia** (registrada, anunciada y con turno), aunque el diputado argumente sin preguntar directamente: lo decide la estructura, no el modelo. En otros formatos decide el modelo (confianza de 0,7 o más).
- **El modelo da el cargo y la cita literal, nunca las cifras.** Qwen recibe lo que lee la Presidencia antes de la primera respuesta del Gobierno y lo que dice quien pregunta (`QuestionBlock.question_text`).
- **Se guarda lo que dijo el modelo en cada bloque** (`modelo_por_pregunta` en `m09.json`: pregunta sí/no, confianza, cargo y cita), aunque no decida el recuento, para evaluarlo frente a la lista oficial de intervenciones: si detecta la pregunta y si acierta el cargo. `no_contadas` dice por qué no entra cada pregunta.
- Resultado en OVH con Qwen3.5-9B: V005 M09 0,75 y M06 40 % de 5; V006 M06 67 % de 3 y M09 0,86 (la referencia es 0,73: la pregunta 13 no tiene anuncio en la transcripción, límite de la #124); V007 M09 0,81 y M06 0 % de 3. V005 y V007 coinciden con la referencia oficial.

## Qué hay
- `decision/questions.py`: dos detectores intercambiables. `QuestionRulesEngine` (reglas, sin modelo: la línea base, el «antes») y `LLMQuestionEngine` (Qwen u otro modelo por API compatible con OpenAI, con las mismas defensas que el motor de género: sin herramientas, respuesta JSON cerrada, texto delimitado como dato y una pregunta solo vale con una cita literal del texto). **El modelo marca preguntas; no cuenta nada**: las cifras las calcula el código.
- `evaluation/questions_eval.py`: mide un detector contra la anotación (precisión, cobertura y F1 de la clase «pregunta», matriz de confusión, % a revisión, tokens). `python -m evaluation.questions_eval anotadas.csv --engines rules,llm`.
- `evaluation/prepare_questions.py hoja`: hoja para que Ivette anote las preguntas de un tramo (turnos en orden de vídeo, sin etiquetas del sistema). `... hoja --sesion V004 --desde 0:10:00 --hasta 0:30:00` escribe `data/anotacion/preguntas_para_anotar.csv`.
- `evaluation/prepare_questions.py ajuste`: convierte la hoja anotada en los JSONL de entrenamiento y evaluación del ajuste ligero de Qwen, en el formato cerrado del motor. La evaluación va con **otra** sesión. Un positivo sin frase literal no se inventa: se cuenta aparte.

## Ajuste ligero de Qwen: no se hace en esta entrega

Decisión del 26 oct (#51): con la regla anterior, Qwen ya no decide el recuento en las sesiones de control, y su evaluación se hace con `modelo_por_pregunta` frente a la lista oficial. El ajuste con la sesión de desarrollo V008 queda en la hoja de ruta. El procedimiento previsto, por si se retoma:

### Cómo se mediría el ajuste
1. «Antes»: `questions_eval` sobre la sesión de evaluación con el modelo sin ajustar (y con la línea base por reglas).
2. Ajuste ligero (LoRA, float16 en las V100S) con la sesión de entrenamiento.
3. «Después»: la misma evaluación con el modelo ajustado, con el mismo método.
4. Si no mejora más de lo que fijemos con Ivette, se conserva el modelo sin ajustar y se dice. Los pesos ajustados no se publican ni se suben al repo.

## Prueba de humo en OVH (21 oct 2026)
`finetune/train_lora.py --smoke` (16 ejemplos inventados, 10 pasos, una V100S del notebook, float16, sin NaN):

| Modelo | Memoria pico | 10 pasos | Pérdida |
|---|---|---|---|
| Qwen3.5-4B | 9,3 GB | 37 s | 1,02 → 0,34 |
| Qwen3.5-9B | 19,0 GB | 35 s | 0,95 → 0,33 |

Los dos caben en una V100S de 32 GB y entrenan sin problemas; el 9B es el candidato para el ajuste real. El «antes y después» de esta prueba **no cuenta como resultado**: evalúa con los mismos ejemplos inventados con los que entrena (el 9B ya acertaba el 100 % antes). Los avisos de `causal_conv1d` y `flash-linear-attention` son solo de velocidad.

Si se retoma el ajuste: datos de V008 (desarrollo) y evaluación con V005–V007 frente a la lista oficial, nunca con la misma sesión.
