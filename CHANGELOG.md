# Changelog

Todos los cambios relevantes de este proyecto se documentan en este fichero.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto sigue [Versionado Semántico](https://semver.org/lang/es/).

## [Sin publicar]

### Añadido

- 20 oct 2026: el prompt del motor LLM da ejemplos simétricos para mujer y hombre. En el benchmark sintético, Qwen3.5-9B acertaba todas las mujeres pero dejaba hasta 22 de 69 hombres en «desconocido» aunque el contexto dijera «el señor…» (el único ejemplo del prompt era femenino); además el resultado varía entre ejecuciones.
- 20 oct 2026: `evaluation.benchmark` lee el `.env` (antes fallaba con «falta LLM_MODEL»).
- 20 oct 2026: medida real con Qwen3.5-9B en OVH AI Endpoints: `reasoning_effort: none` baja de 1.121 a 63 tokens de salida y de 38,9 a 3,6 s por llamada (`docs/COSTES_API.md`).
- 20 oct 2026: `evaluation.benchmark --detalle <carpeta>` guarda la decisión de cada turno (CSV) para analizar los errores de cada motor. Con los turnos sintéticos, Qwen3.5-9B por API: F1 0,76, sin confundir nunca mujer con hombre, 18 de 69 hombres a «desconocido», 0,0055 € por 120 turnos.
- 20 oct 2026: `LLM_EXTRA_BODY` (JSON, sin `tools`, `messages`, `model` ni `response_format`) y `LLM_MAX_TOKENS` para el motor LLM, para quitar el razonamiento de Qwen 3 (en la prueba con Qwen3.5-9B: 1.121 tokens de salida y 39 s para una respuesta de ~30 tokens).
- 20 oct 2026: `python -m decision.llm_check` lista los modelos de la API (OVH AI Endpoints u otra compatible con OpenAI) y hace una llamada de prueba sintética con tokens y coste; `docs/COSTES_API.md` con los modelos Qwen candidatos y sus precios del catálogo público (20 oct).
- 20 oct 2026: la seudonimización estricta también redacta un apellido suelto que sea una frase entera («Uriarte.») salvo palabras comunes (lista `common` de `decision/cues/es.toml`); detectado en V004 (1 h 19 min, 12 voces, 8 con género por pistas del lenguaje) procesado en la GPU de OVH en 7 min 22 s.
- 20 oct 2026: prueba de humo en el notebook de OVH (2×V100S): `volta_sm70_supported: true`, transcripción `large-v3` en float16 y separación de voces correctas. WhisperX pasa al extra opcional `[align]` (fija torch 2.8 y rompería el PyTorch del notebook); el Dockerfile lo instala con `[pipeline,align]`. `docs/PRUEBA_GPU.md` documenta la vía del notebook.
- 19 oct 2026: seudonimización en modo estricto (cualquier palabra con mayúscula a mitad de frase fuera de una lista de excepciones se sustituye), `pipeline.reanalyze` para repetir el análisis sin volver a transcribir, y pista débil `floor_grant_same_voice` (< 0,7, solo sugerencia en la revisión) cuando la diarización junta a la Presidencia con quien habla. `docs/SEUDONIMIZACION.md`. Dos skills del proyecto en `.claude/skills/` (`procesar-sesion`, `revisar-antes-de-publicar`).
- 19 oct 2026: esqueleto del panel en `dashboard/` (Streamlit): pantalla de sesión (tarjetas M01–M04 y M13, gráficos, línea de tiempo, tabla de intervenciones sin nombres, informe HTML descargable) y pantalla de evolución, con datos sintéticos o `data/processed/`. `streamlit run dashboard/app.py`. M09 y M14 aparecen como «no disponible todavía». 5 pruebas, incluida la carga de la app.
- 19 oct 2026: `metrics/borrador.py` con M01, M02, M03, M04 y M13 en BORRADOR (definiciones de una línea del README; mínimos de muestra provisionales), pendientes de la definición formal de Ivette. 7 pruebas con casos hechos a mano.
- 19 oct 2026: `decision/pseudonymize.py`: seudonimización. Cada voz es «Persona N»; los nombres tras un tratamiento («la señora X», «me llamo X») se sustituyen por el código de la voz o uno nuevo; `Speaker.name` se vacía; la tabla nombre → código no se guarda. `pipeline.analyze` lo aplica antes del género y `resumen.json` trae el mapa voz → «Persona N». Límite: un nombre suelto o escrito en minúscula no se detecta.
- 20 oct 2026: baseline de vídeo sin cara en `pipeline/video.py` (seguimiento de personas por solape de cajas, tiempo en pantalla, tamaño y centralidad por pista; género solo por audio); `evaluation/video_eval.py` (error de conteo, F1 de manos y género de las pistas con «desconocido» aparte); `docs/EVALUACION.md` con el plan de evaluación, la decisión de no usar género por la cara y el texto para la diapositiva «Evaluación y límites».
- 20 oct 2026: `pipeline/video.py` (prototipo): personas visibles y manos levantadas por zona con MediaPipe Pose Landmarker, una pasada a 2 fotogramas por segundo, sin caras, sin identificar y sin guardar imágenes; `python -m pipeline.video data/raw/V001.mp4 --model <modelo.task>` escribe `video.json`. Extra `[video]`. El modelo `.task` no se incluye.
- 20 oct 2026: evaluación de costes de la API: `Decision.tokens_in/tokens_out` (campos opcionales, del `usage` de la respuesta), `evaluation/cost.py` (precios por variables de entorno, sin valores en el código; coste por turno y por sesión; previsión) y coste junto al F1 en `evaluation.benchmark`. `docs/COSTES_API.md`.
- 19 oct 2026: la diarización lee el WAV con la librería estándar (`load_waveform`) y se lo pasa a pyannote como forma de onda, para no depender de torchcodec, que en Windows exige las DLL «shared» de FFmpeg. Probado en CPU: transcripción y diarización con un tono sintético.
- 19 oct 2026: `pyannote/speaker-diarization-3.1` necesita aceptar también las condiciones de `pyannote/speaker-diarization-community-1` (restringido).
- 19 oct 2026: `pipeline/envfile.py`: `pipeline.run` y `pipeline.smoke` leen el fichero `.env` (antes solo leían variables de entorno, así que `HF_TOKEN` y el resto del `.env` se ignoraban). Lo ya definido en el entorno manda.
- 19 oct 2026: se fija `av<19` en el extra `[pipeline]` y en `docker/constraints.txt`: con av 19.0.1, faster-whisper 1.2.1 falla con `TypeError: open() got an unexpected keyword argument 'metadata_errors'`.
- 19 oct 2026: `pipeline/analyze.py` y `pipeline.run` encadenan el género por lenguaje y escriben `resumen.json` (tiempo de palabra por género, muestra y aviso de método) y `review_genero.csv` (solo voces dudosas).
- Bloque A (17 oct 2026, rama `docker-gpu`): `docker/` con imagen CPU y GPU (V100S, float16/int8), `docker-compose.yml`, `.dockerignore`; `make smoke` (`pipeline/smoke.py`) que mide tiempo y memoria en un JSON; `docs/PRUEBA_GPU.md`. Sin probar aún en GPU.
- Bloque B (17 oct 2026, rama `fuente-congreso`): `sources/` con la interfaz `VideoSource` (RF-19), el adaptador del Congreso, el validador del manifiesto y la negativa de `pipeline/run.py` a analizar vídeos sin fila completa; `source.json` con la cita de fuente y fecha; descarga automática desactivada y sin código de red. `docs/FUENTE_CONGRESO.md`.
- Bloque E (17 oct 2026, rama `decision-motores`, parte de `genero-lenguaje`): `DecisionEngine`, `RulesEngine` y `LLMEngine` (API compatible con OpenAI, sin herramientas, salida cerrada por esquema, evidencia literal obligatoria, rechaza `nimble-v3`); `evaluation/benchmark.py` con F1 por clase; test con transcripción hostil. `docs/MOTORES_DECISION.md`.
- Bloque C (17 oct 2026, rama `genero-lenguaje`): `decision/gender_cues.py` y `decision/cues/es.toml`: género por pistas del lenguaje con evidencia (frase, minuto, método, confianza), `desconocido` y fila de revisión si no hay pista o se contradicen. Pendiente de validar por Ivette. `docs/GENERO_LENGUAJE.md`.
- `contracts/` (solo opcional): valor `GenderSource.LANGUAGE_CUE`, clase `GenderEvidence` y `Speaker.gender_evidence` (vacío por defecto).
- Bloque D (17 oct 2026, rama `metricas-marco`): `metrics/` con registro de métricas, `MetricResult` con la regla de «no concluyente» por muestra insuficiente, utilidades de tiempo de palabra por voz y por género (con `desconocido` y `sin_atribuir` aparte) y una métrica de ejemplo `X00_EJEMPLO`. No define M01 a M13 ni umbrales (de Ivette). Nueva dependencia: pandas. `docs/METRICAS_MARCO.md`.
- Bloque F (17 oct 2026, rama `datos-sinteticos`): `evaluation/synthetic/` genera datos SINTÉTICOS con semilla fija (5 escenarios, con `desconocido`, tiempo sin atribuir y muestra insuficiente) en `evaluation/synthetic/muestras/`; `make synthetic`; `docs/DATOS_SINTETICOS.md`.
- Bloque G (17 oct 2026, rama `manos-levantadas`, prototipo): `pipeline/gestures.py` con `raised_hands` y `detect_raises`, funciones puras sobre puntos de pose (muñeca por encima del hombro); sin imagen, sin reconocimiento facial, sin dependencias nuevas. Probado solo con puntos sintéticos; MediaPipe aún no conectado.
- M2, 16 de octubre de 2026: `pipeline/` con extracción de audio, transcripción (faster-whisper + WhisperX), diarización (pyannote), línea de tiempo, CSV de revisión y punto de entrada `make pipeline`; extra opcional `[pipeline]` y licencias verificadas.
- M1, 16 de octubre de 2026: estructura del repositorio (`contracts/`, `pipeline/`, `decision/`, `metrics/`, `evaluation/`, `dashboard/`, `docker/`, `docs/`, `tests/`).
- Esquemas Pydantic en `contracts/`: `AnalysisEvent`, `AnalysisTimeline`, `Speaker`, tabla de revisión de voces (`ReviewRow`) y tabla de gestos de levantar la mano (`GestureRow`), con lectura y escritura de CSV.
- Regla de género en el esquema: solo `mujer`, `hombre` o `desconocido`, siempre con su fuente; nunca se infiere de la cara ni de la voz.
- 23 tests con datos sintéticos, `Makefile` (`make test`, `make lint`, `make check`) y CI de GitHub Actions.
- Licencia Apache-2.0 y `THIRD_PARTY_LICENSES.md` con las dependencias instaladas verificadas.
- `README.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md` y `CLAUDE.md`.

### Cambiado

- 20 oct 2026 (documentación): `MEMORY.md` con el estado a 20 oct, las reglas de trabajo y cómo citar las fuentes en las presentaciones.
- 20 oct 2026 (documentación): en `docs/PLAN_DE_TRABAJO.md`, la consulta a la Organización sobre la base legal y los formularios de consentimiento pasan a opcionales; se elimina de la documentación la referencia a un artículo concreto de los términos, que no estaba verificada. Las fuentes se citan en las presentaciones.
- 19 oct 2026 (documentación): plan de la entrega ajustado a las bases y a 2 h por persona y día laborable (`docs/PLAN_DE_TRABAJO.md`); alcance de 3 sesiones y métricas M01, M02, M03, M04, M13, M14 y M09; ajuste ligero de Qwen; especificación del panel (`docs/PANEL.md`); README con componentes de terceros y hoja de ruta; actualizados `MEMORY.md`, `CLAUDE.md`, `docs/MODEL_CARD.md` y `docs/DATASET_CARD.md`.
- 16 de octubre de 2026 (decisiones de Sabrina, en documentación; código pendiente): fuente única, sesiones del Congreso sin alterar; alcance "Observatorio MVP" (6 a 10 sesiones, descarga automática de prueba, dashboard de evolución); género por pistas del lenguaje con revisión humana solo si hay duda; nuevas métricas de equidad (M17 a M19); avisos en sala, informe y alta de fuente.

### Pendiente

- Probar el código en la GPU de OVH con un vídeo corto.
- Métricas de esta entrega (definiciones de Ivette), panel en Streamlit, M09 y ajuste ligero de Qwen.
- Confirmar si el Congreso permite la descarga automática (evolución futura).
