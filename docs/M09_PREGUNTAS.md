# M09 · preguntas recibidas (andamiaje)

**Estado:** la definición de M09 es de Ivette y **sigue pendiente**. Lo de aquí está preparado para que, cuando llegue, solo haya que conectarla. Definición **provisional** que usa el código: una pregunta es una frase del turno que formula una pregunta, con signos de interrogación o con una fórmula interrogativa. Falta fijar qué cuenta, a quién se atribuye (quien pregunta, quien responde o a quien va dirigida) y cómo se reparte por género.

## Qué hay
- `decision/questions.py`: dos detectores intercambiables. `QuestionRulesEngine` (reglas, sin modelo: la línea base, el «antes») y `LLMQuestionEngine` (Qwen u otro modelo por API compatible con OpenAI, con las mismas defensas que el motor de género: sin herramientas, respuesta JSON cerrada, texto delimitado como dato y una pregunta solo vale con una cita literal del texto). **El modelo marca preguntas; no cuenta nada**: las cifras las calcula el código.
- `evaluation/questions_eval.py`: mide un detector contra la anotación (precisión, cobertura y F1 de la clase «pregunta», matriz de confusión, % a revisión, tokens). `python -m evaluation.questions_eval anotadas.csv --engines rules,llm`.
- `evaluation/prepare_questions.py hoja`: hoja para que Ivette anote las preguntas de un tramo (turnos en orden de vídeo, sin etiquetas del sistema). `... hoja --sesion V004 --desde 0:10:00 --hasta 0:30:00` escribe `data/anotacion/preguntas_para_anotar.csv`.
- `evaluation/prepare_questions.py ajuste`: convierte la hoja anotada en los JSONL de entrenamiento y evaluación del ajuste ligero de Qwen, en el formato cerrado del motor. La evaluación va con **otra** sesión. Un positivo sin frase literal no se inventa: se cuenta aparte.

## Cómo se mide el ajuste de Qwen (28 oct)
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

Pendiente: la definición de Ivette, la anotación (#52) y los datos reales de ajuste y de evaluación (sesiones distintas).
