# Herramientas de VIS Open y coste por sesión

Resumen para la presentación: qué herramienta usa cada paso, para qué sirve, qué regla cumple y cuánto cuesta. Licencias completas en `THIRD_PARTY_LICENSES.md`; proveedores y datos en `docs/PROVEEDORES.md`.

## Cadena de análisis

| Paso | Herramienta | Qué hace | Dónde corre | Licencia |
|---|---|---|---|---|
| 1. Fuente | Vídeos del Congreso (emisión oficial), Diario de Sesiones y datos abiertos de diputadas y diputados (`sources/`) | Vídeo original sin alterar, referencia oficial para validar y composición de la cámara | Descarga manual, fuera del repositorio | Aviso legal del Congreso (reutilización citando la fuente) |
| 2. Audio | FFmpeg | Extrae el audio del bloque de preguntas (tramo del manifiesto) | Local / OVH | LGPL-2.1+ |
| 3. Transcripción | faster-whisper (Whisper large-v3) | Convierte la voz en texto con tiempos por palabra | GPU de OVH (V100S) | MIT |
| 4. Separación de voces | pyannote 3.1 (+ segmentación y wespeaker) | Dice quién habla en cada momento (SPEAKER_00, 01…), sin identificar a nadie | GPU de OVH | MIT; wespeaker CC-BY-4.0 (atribución en `NOTICE`) |
| 5. Seudonimización | Código propio (`decision/pseudonymize.py`) | Cambia los nombres por «Persona N» antes de cualquier otro uso | Local / OVH | Del proyecto |
| 6. Género | Reglas del lenguaje propias (`decision/gender_cues.py`, `cues/es.toml`) | Asigna mujer/hombre solo por palabras dichas en sala («la diputada doña…», «Señora ministra»); si no hay pista, «desconocido» | Local / OVH | Del proyecto |
| 7. Roles y preguntas | Código propio (`decision/roles.py`) | Encuentra a la Presidencia, cada pregunta, quién pregunta y quién responde (16, 18 y 19 de 17, 19 y 20 oficiales) | Local / OVH | Del proyecto |
| 8. IA de lenguaje | Qwen3.5-9B (OVH AI Endpoints o servidor propio) | Confirma si un turno es una pregunta y copia el cargo al que se dirige (M09, M06). Sin herramientas, respuesta JSON cerrada, cita literal obligatoria; confianza < 0,7 → revisión humana. **No calcula ninguna cifra** | API compatible con OpenAI | Apache-2.0 |
| 9. Ajuste de Qwen | transformers + peft (LoRA) | Adapta Qwen a las preguntas del Congreso con una sesión de desarrollo (no con las de evaluación) | GPU de OVH | Apache-2.0 |
| 10. Métricas | pandas (`metrics/`) | Calcula M01–M13 de forma determinista; «no concluyente» si no hay muestra suficiente | Local | BSD-3-Clause |
| 11. Revisión humana | Panel, «Human in the loop» | Dos anotadoras validan el género de las voces dudosas; cuenta cuando coinciden | Local | Del proyecto |
| 12. Vídeo (opcional) | MediaPipe Pose + OpenCV | Personas visibles y tiempo en pantalla (el género sale del audio, nunca de la imagen; sin caras) | CPU local | Apache-2.0 |
| 13. Panel e informe | Streamlit + Altair + ReportLab | Panel accesible, gráficos, informe PDF, subtítulos (.vtt) | Local | Apache-2.0 / BSD |
| 14. Asistente de voz | Whisper large-v3-turbo (API de OVH) + voz del navegador | Órdenes habladas para personas con discapacidad visual; la voz de respuesta es local | API (solo la orden hablada) | MIT |

Reglas que cumple la cadena: todo en local salvo las dos API opcionales; el género nunca sale de la cara ni de la voz; las cifras las calcula el código, nunca el LLM; cada dato lleva su procedencia; nada de audio, vídeo ni transcripciones reales en el repositorio.

## Sesiones analizadas

| Id | Sesión | Uso |
|---|---|---|
| V004 | Diputación Permanente, sesión 8 (16/10/2026), punto RDL 24/2026 | Desarrollo (otro formato; no se compara) |
| V005 | Pleno, sesión 202 (30/09/2026), sesión de control, XV legislatura | Evaluación |
| V006 | Pleno, sesión 207 (05/10/2022), sesión de control, XIV legislatura | Evaluación |
| V007 | Pleno, sesión 142 (19/09/2018), sesión de control, XII legislatura | Evaluación |

## Coste estimado de API por sesión (Qwen, M09)

Lo único que factura por uso es Qwen: una llamada por pregunta detectada, con el texto de quien pregunta. **Estimación**, no medición: tokens de entrada ≈ 1,5 × palabras + 300 por llamada (instrucciones), salida ≈ 70 por llamada (medido el 20 oct con `reasoning_effort: none`: 350 / 63 tokens). Precios del catálogo de OVH consultado el 20 oct 2026 (volver a comprobarlos el día de la medición): Qwen3.5-9B 0,10 € / 0,15 € por millón de tokens; Qwen 27B 0,40 € / 2,70 €.

| Id | Preguntas (llamadas) | Palabras de quien pregunta | Tokens entrada / salida | Coste con 9B | Coste con 27B |
|---|---|---|---|---|---|
| V004 | 5 | 6.935 | ≈ 11.900 / 350 | ≈ 0,0012 € | ≈ 0,006 € |
| V005 | 16 | 6.985 | ≈ 15.300 / 1.120 | ≈ 0,0017 € | ≈ 0,009 € |
| V006 | 18 | 7.569 | ≈ 16.800 / 1.260 | ≈ 0,0019 € | ≈ 0,010 € |
| V007 | 19 | 8.065 | ≈ 17.800 / 1.330 | ≈ 0,0020 € | ≈ 0,011 € |
| **Total** | 58 | 29.554 | ≈ 61.800 / 4.060 | **≈ 0,007 €** | **≈ 0,036 €** |

Para otras instituciones: con 9B, unos **0,2 € por cada 100 sesiones** de control.

**Medición del 23 oct 2026** (OVH AI Endpoints, modelo fijo `Qwen3.5-9B`, no un modelo virtual, para que el resultado se pueda repetir; `reasoning_effort: none`):

- Llamada de prueba (`python -m decision.llm_check`, turno sintético): **437 tokens de entrada / 63 de salida, 3,4 s**. Con los precios de arriba, unos 0,00005 € por llamada.
- M09 y M06 con Qwen en V005–V007: **55 llamadas** (17 / 18 / 20, una por pregunta detectada tras la PR #126), unos 3–5 minutos en total, sin errores.
- `m09.json` todavía no guarda los tokens de cada sesión: el coste por sesión de la tabla sigue siendo una estimación (≈ 0,002 €), coherente con la llamada medida. Las cifras de preguntas de la tabla son de antes de la PR #126.
- A Qwen solo le llega texto seudonimizado («Persona N»), nunca audio ni nombres.
- V004 (Diputación Permanente) es ahora una demo de otro formato: no se le calcula M09.

## Coste total por sesión (GPU + API)

Lo caro no es Qwen, sino la **GPU** que transcribe y separa las voces. Precios del tarifario oficial de OVHcloud (sin IVA), consultado el 23 oct 2026 en https://www.ovhcloud.com/es-es/public-cloud/prices/ :

| Servicio | Precio |
|---|---|
| GPU Tesla V100S, AI Notebooks / AI Training (`ai1-1-gpu`) | 1,93 €/hora (`ai1-le-1-gpu`: 0,90 €/hora) |
| Qwen3.5-9B (AI Endpoints) | 0,10 € / 0,15 € por millón de tokens (entrada / salida) |
| Whisper large-v3 / large-v3-turbo (AI Endpoints, alternativa a la GPU propia) | 0,147 € / 0,046 € por hora de audio |

El 23 oct cada sesión de control (unos 100–112 min de bloque de preguntas) tardó **unos 10–15 minutos de GPU** en transcribirse y separar voces (medida aproximada; falta medirla con precisión):

| Id | Minutos analizados | GPU (≈ 10–15 min a 1,93 €/h) | Qwen (M09) | **Total aprox.** |
|---|---|---|---|---|
| V004 | 79 | 0,30–0,50 € | 0,0012 € | **≈ 0,3–0,5 €** |
| V005 | 99 | 0,30–0,50 € | 0,0017 € | **≈ 0,3–0,5 €** |
| V006 | 112 | 0,30–0,50 € | 0,0019 € | **≈ 0,3–0,5 €** |
| V007 | 112 | 0,30–0,50 € | 0,0020 € | **≈ 0,3–0,5 €** |

Es poco porque la GPU procesa unas 7–10 veces más rápido que la duración del vídeo. **Ojo:** la GPU se factura por hora **encendida**, procese o no (1,93 € × 24 h ≈ 46 €/día): en producción hay que apagarla al terminar cada lote. El reto pone la máquina; estas cifras son lo que costaría a otra institución.

Otros costes, sin tarifa por uso:
- **Análisis de vídeo** en CPU local: unos 18 min para V005.
- **Asistente de voz** (opcional, por uso): una llamada de Whisper por orden hablada y, si se pide, un resumen con Qwen. Precio por verificar en el catálogo de OVH.
- **Ajuste de Qwen**: horas de GPU de OVH (el 9B cabe en una V100S: 19 GB).
