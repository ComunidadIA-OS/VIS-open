# Changelog

Todos los cambios relevantes de este proyecto se documentan en este fichero.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto sigue [Versionado Semántico](https://semver.org/lang/es/).

## [Sin publicar]

### Añadido

- Bloque D (17 oct 2026, rama `metricas-marco`): `metrics/` con registro de métricas, `MetricResult` con la regla de «no concluyente» por muestra insuficiente, utilidades de tiempo de palabra por voz y por género (con `desconocido` y `sin_atribuir` aparte) y una métrica de ejemplo `X00_EJEMPLO`. No define M01 a M13 ni umbrales (de Ivette). Nueva dependencia: pandas. `docs/METRICAS_MARCO.md`.
- M2, 16 de octubre de 2026: `pipeline/` con extracción de audio, transcripción (faster-whisper + WhisperX), diarización (pyannote), línea de tiempo, CSV de revisión y punto de entrada `make pipeline`; extra opcional `[pipeline]` y licencias verificadas.
- M1, 16 de octubre de 2026: estructura del repositorio (`contracts/`, `pipeline/`, `decision/`, `metrics/`, `evaluation/`, `dashboard/`, `docker/`, `docs/`, `tests/`).
- Esquemas Pydantic en `contracts/`: `AnalysisEvent`, `AnalysisTimeline`, `Speaker`, tabla de revisión de voces (`ReviewRow`) y tabla de gestos de levantar la mano (`GestureRow`), con lectura y escritura de CSV.
- Regla de género en el esquema: solo `mujer`, `hombre` o `desconocido`, siempre con su fuente; nunca se infiere de la cara ni de la voz.
- 23 tests con datos sintéticos, `Makefile` (`make test`, `make lint`, `make check`) y CI de GitHub Actions.
- Licencia Apache-2.0 y `THIRD_PARTY_LICENSES.md` con las dependencias instaladas verificadas.
- `README.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md` y `CLAUDE.md`.

### Cambiado

- 16 de octubre de 2026 (decisiones de Sabrina, en documentación; código pendiente): fuente única, sesiones del Congreso sin alterar; alcance "Observatorio MVP" (6 a 10 sesiones, descarga automática de prueba, dashboard de evolución); género por pistas del lenguaje con revisión humana solo si hay duda; nuevas métricas de equidad (M17 a M19); avisos en sala, informe y alta de fuente.

### Pendiente

- Confirmar si el Congreso permite la descarga automática (robots de app.congreso.es).

- Probar el pipeline de M2 con un vídeo de prueba en la VM de OVH.
- Motores de decisión, métricas deterministas (a validar por Ivette), panel en Streamlit y Docker.
