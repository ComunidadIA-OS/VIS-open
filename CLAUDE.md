# CLAUDE.md · Mujeres por la IA Abierta

Instrucciones para cualquier sesión de Claude Code que trabaje en este repositorio. Lee también `MEMORY.md` y `SKILLS.md`.

## Qué es
Herramienta abierta y local que mide, a partir del audio y el vídeo de debates (sin reconocimiento facial), la presencia, participación, protagonismo y representación de las mujeres. Reto "Mujeres por la IA Abierta" (SEDIA / Comunidad IA de Código Abierto).
Entregas: antes del 30 oct 2026 a las 08:00, repositorio público, README y .pptx; antes del 4 nov a las 08:00, vídeo de 5 minutos y presentación corta. Cierre del código: 28 oct. Plan detallado: `docs/PLAN_DE_TRABAJO.md`.

## Estado: M1, M2 y prompt M3 hechos y en `main` (19 oct 2026)
- M1 (hecho) = estructura del repo, esquemas Pydantic (`contracts/`), CI, `make test` y `THIRD_PARTY_LICENSES.md`.
- M2 (hecho, rama `m2-pipeline`) = audio, transcripción, diarización, línea de tiempo y CSV de revisión.
- Prompt M3 (hecho): Docker CPU/GPU, fuente Congreso y manifiesto, género por lenguaje, marco de métricas, motores de decisión, datos sintéticos y detector de mano levantada. `pipeline.run` ya encadena transcripción → diarización → género por lenguaje → `resumen.json`.
- Alcance de la entrega (19 oct): 3 sesiones; métricas M01, M02, M03, M04, M13, M14 y M09; ajuste ligero de Qwen. El resto es evolución futura.
- Pendiente: prueba real en OVH (GPU), definiciones de Ivette (incluida M09), panel, integración de M09 y ajuste del modelo (Sabrina), código de M09 y plan de puesta en producción (Veru).
- Licencia Apache-2.0 aprobada por Sabrina (16 oct 2026); falta comunicarla a Ivette y Veru.
- El vídeo (gestos de levantar la mano) está en el MVP y no se propone como opcional; sin reconocimiento facial.
- Fuente del MVP (16 oct): solo sesiones del Congreso, sin modificar ni alterar el vídeo; los vídeos nunca van al repo. Para el ajuste ligero de Qwen (19 oct) solo se usa el texto transcrito de una sesión, comprobado con el Diario de Sesiones; nunca audio, vídeo ni voz. El modelo ajustado no se publica.
- Infra: desarrollo y pruebas pequeñas en local (CPU); transcripción, diarización y LLM en las VM de OVHcloud (2 espacios, 2×V100S cada uno; Volta: float16/int8, sin bf16). OVH se usa de forma prioritaria. Credenciales nunca en el repo.
- Documentos de referencia: propuesta de arquitectura y PRD (enlaces en `MEMORY.md`).
- Las métricas (sección 5 del PRD) son un borrador hasta el visto bueno de Ivette.

## Equipo y propiedad
- Sabrina: dirección, arquitectura e integración, pipeline de IA, panel en Streamlit, infraestructura, RGPD y AI Act.
- Ivette: define y valida las métricas (no programa), anotación de referencia y presentación .pptx.
- Veru: datos, programa las métricas, plan de puesta en producción y revisión del repositorio.
- Cada persona dispone de unas 2 h por día laborable.
Cada carpeta tiene una persona responsable; los cambios en carpetas ajenas se proponen por PR.

## Arquitectura en una línea
vídeo → audio (FFmpeg) + gestos (OpenCV/MediaPipe) → faster-whisper + WhisperX → pyannote → línea de tiempo `AnalysisEvent` (Pydantic) → revisión humana (CSV) → `DecisionEngine` → métricas deterministas (pandas) → Streamlit.

## Reglas inamovibles
1. Código ejecutable en local (CPU) para pruebas pequeñas; el análisis pesado corre en OVHcloud. Ninguna clave de pago es obligatoria para usar el proyecto, y las credenciales nunca van al repositorio.
2. No se guardan nombres (19 oct): cada voz es «Persona 1», «Persona 2»…; en la evidencia y en las transcripciones el nombre se sustituye por el código. El género nunca se infiere de la cara ni de la voz (tampoco del tono). Fuentes permitidas (16 oct): pistas del lenguaje de la transcripción con evidencia («la señora / el señor X»), declarado, registro público o revisión humana; si no, `desconocido` (siempre visible).
3. Las cifras las calcula el código (pandas). El LLM nunca calcula ni resume números.
4. El LLM no tiene herramientas, devuelve JSON cerrado por gramática, validado con Pydantic. Confianza <0,7 → revisión humana. Los datos van delimitados de las instrucciones.
5. Conclusiones solo si la brecha supera el umbral (15 puntos, a fijar por Ivette), el tiempo sin atribuir es menor que la brecha y el resultado resiste los márgenes de error. Si no: "no concluyente".
6. Cada dato lleva procedencia: `observed`, `computed`, `ai_inferred` o `human_validated`.
7. Nunca se sube al repo audio, vídeo, transcripciones reales ni secretos. Los datos viven fuera (`data/` ignorado).
8. Modelos: usar `nimble` (Apache 2.0), NUNCA `nimble-v3` (CC BY-NC). Jev queda descartado. Kev es experimental (solo inglés). Sin LangChain: motor propio `DecisionEngine` contra una API compatible con OpenAI, agnóstico al modelo.
9. Toda dependencia nueva se anota en `THIRD_PARTY_LICENSES.md` con su licencia verificada en la fuente, no de memoria.
10. Decisiones importantes (licencia, alcance, datos, motores) las aprueba Sabrina antes de implementarse.

## Hardware
Portátiles (CPU, clips cortos) y VM OVHcloud con 2×V100S (Volta: sin bf16; usar float16 o int8, versiones fijadas en el Dockerfile).

## Estructura prevista del repo (M1)
`contracts/`, `pipeline/`, `decision/`, `metrics/`, `evaluation/`, `dashboard/`, `tests/`, `docker/`, `docs/`, `THIRD_PARTY_LICENSES.md`, `Makefile`, `.env.example`.

## Cómo trabajar
- Idioma de documentos y mensajes: español. Código y nombres de variables: inglés.
- Cambios pequeños, un PR por tarea, con tests de las métricas y de los contratos.
- Tras cada cambio: `make test` en verde antes de pedir revisión.
- Si algo es ambiguo, elige un valor razonable por defecto, anótalo en el PR y sigue.
- Requisitos y criterios de aceptación: usa los IDs del PRD (RF-xx, RNF-xx, Mxx).

## Requisitos del reto a no olvidar
Repo público dentro de la organización GitHub de la Comunidad IA de Código Abierto; licencia OSI/FSF; README con licencias de terceros y hoja de ruta; pptx de hasta 20 diapositivas; vídeo de 5 minutos; uso de LLM agnóstico al modelo. Puntuación: calidad técnica 30, impacto 15, innovación 15, género 10, open source 10, comunicación 10, ética y normativa 5, despliegue 5.

## Siguientes tareas (plan del 19 oct)
El plan completo está en `docs/PLAN_DE_TRABAJO.md` y la especificación del panel en `docs/PANEL.md`. Siguientes tareas de código, en orden:
1. Prueba del código en la GPU de OVH (20 oct, Sabrina; `docs/PRUEBA_GPU.md`).
2. Transcripción y separación de voces de las 3 sesiones (21–22 oct, Sabrina).
3. Código anónimo y género de cada voz (23 oct, Sabrina; `decision/gender_cues.py`).
4. Métricas M01, M02, M03, M04 y M13 con pandas y pytest (Veru).
5. Manos levantadas con OpenCV y MediaPipe (26 oct, Sabrina) y M14 (Veru).
6. M09 con Qwen a través de una API compatible con OpenAI, sin depender de un modelo concreto (27 oct): métrica de Ivette, código de Veru, integración de Sabrina.
7. Panel en Streamlit según `docs/PANEL.md` (Sabrina).
8. Ajuste ligero de Qwen (28 oct, Sabrina): solo con texto seudonimizado; el modelo ajustado no se publica.
9. Cierre del código el 28 oct.
10. Repositorio público antes del 30 oct a las 08:00.

Fechas límite:
- 30 oct a las 08:00: repositorio público, README y .pptx de 20 diapositivas como máximo.
- 3 nov: vídeo montado enviado al equipo para revisarlo.
- Antes del 4 nov a las 08:00: vídeo de 5 minutos y presentación corta.
