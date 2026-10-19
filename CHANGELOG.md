# Changelog

Todos los cambios relevantes de este proyecto se documentan en este fichero.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto sigue [Versionado Semántico](https://semver.org/lang/es/).

## [Sin publicar]

### Añadido

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

- 19 oct 2026 (documentación): plan de la entrega ajustado a las bases y a 2 h por persona y día laborable (`docs/PLAN_DE_TRABAJO.md`); alcance de 3 sesiones y métricas M01, M02, M03, M04, M13, M14 y M09; ajuste ligero de Qwen; especificación del panel (`docs/PANEL.md`); README con componentes de terceros y hoja de ruta; actualizados `MEMORY.md`, `CLAUDE.md`, `docs/MODEL_CARD.md` y `docs/DATASET_CARD.md`.
- 16 de octubre de 2026 (decisiones de Sabrina, en documentación; código pendiente): fuente única, sesiones del Congreso sin alterar; alcance "Observatorio MVP" (6 a 10 sesiones, descarga automática de prueba, dashboard de evolución); género por pistas del lenguaje con revisión humana solo si hay duda; nuevas métricas de equidad (M17 a M19); avisos en sala, informe y alta de fuente.

### Pendiente

- Probar el código en la GPU de OVH con un vídeo corto.
- Métricas de esta entrega (definiciones de Ivette), panel en Streamlit, M09 y ajuste ligero de Qwen.
- Confirmar si el Congreso permite la descarga automática (evolución futura).
