# CLAUDE.md · Mujeres por la IA Abierta

Instrucciones para cualquier sesión de Claude Code que trabaje en este repositorio. Lee también `MEMORY.md` y `SKILLS.md`.

## Qué es
Herramienta abierta y local que mide, a partir del audio y el vídeo de debates (sin reconocimiento facial), la presencia, participación, protagonismo y representación de las mujeres. Reto "Mujeres por la IA Abierta" (SEDIA / Comunidad IA de Código Abierto).
Entregas: antes del 30 oct 2026 a las 08:00, repositorio público, README y .pptx; antes del 4 nov a las 08:00, vídeo de 5 minutos y presentación corta. Cierre del código: 28 oct. Plan detallado: `docs/PLAN_DE_TRABAJO.md`.

## Estado (29 oct 2026)
- Código cerrado y en `main`: pipeline completo (audio, transcripción, separación de voces, seudonimización «Persona N», género por pistas del lenguaje, vídeo sin cara, métricas, panel) probado en OVHcloud con 2×V100S. 490 pruebas en verde y lint limpio.
- Sesiones de evaluación: V005 (30/09/2026), V006 (05/10/2022) y V007 (19/09/2018).
- Métricas de la entrega: M01, M02 (con M02b), M03a, M03b, M04, M06, M09 y M13. Definiciones de Ivette en `docs/metricas.md`. Descartadas para el Congreso: M05, M08, M10 y M14–M16.
- Validación de Ivette (25–27 oct) frente a la lista oficial de intervenciones del Congreso: 87/87 personas, 86 con el género correcto, 0 errores y 1 a revisión humana; M06 coincide en las 3 sesiones y M09 en 2 de 3 (`docs/EVALUACION.md`).
- Panel en Streamlit con Human in the loop, asistente de voz y modo manos libres (estos dos, en beta).
- Plan de puesta en producción: `docs/PRODUCCION.md` y `docs/PRODUCCION_RGPD_AIACT.md` (29 oct), sin validación jurídica.
- Vídeo explicativo y presentaciones (completa y corta) publicados como Releases.
- Hoja de ruta (no hecho en la entrega): ajuste ligero de Qwen con V008, DER y WER exacto con un tramo anotado a mano, más sesiones y más métricas (ver README).
- Licencia Apache-2.0 aprobada por Sabrina (16 oct 2026).
- Vídeo: personas visibles y tiempo en pantalla a partir de la postura del cuerpo, sin reconocimiento facial; el género en pantalla se hereda de la voz.
- Fuente (16 oct): solo sesiones del Congreso, sin modificar ni alterar el vídeo; los vídeos nunca van al repo. Para el ajuste ligero de Qwen (19 oct) solo se usa el texto transcrito de una sesión, comprobado con el Diario de Sesiones; nunca audio, vídeo ni voz. El modelo ajustado no se publica.
- Infra: desarrollo y pruebas pequeñas en local (CPU); transcripción, diarización y LLM en las VM de OVHcloud (2 espacios, 2×V100S cada uno; Volta: float16/int8, sin bf16). OVH se usa de forma prioritaria. Credenciales nunca en el repo.
- Documentos de referencia: propuesta de arquitectura y PRD (enlaces en `MEMORY.md`).
- En la documentación no se usa la palabra «borrador» (29 oct).

## Equipo y propiedad
- Sabrina: arquitectura e integración, pipeline de IA, panel en Streamlit, infraestructura, RGPD y AI Act, plan de puesta en producción, vídeos, presentación del 04.11 y publicación.
- Ivette: definición y validación de las métricas (no programa), evaluación del modelo, revisión del código, del panel y de la seudonimización, y presentación .pptx.
- Veru: programación de las métricas.
- Cada persona dispone de unas 2 h por día laborable.
Cada carpeta tiene una persona responsable; los cambios en carpetas ajenas se proponen por PR.

## Arquitectura en una línea
vídeo → audio (FFmpeg) + gestos (OpenCV/MediaPipe) → faster-whisper + WhisperX → pyannote → línea de tiempo `AnalysisEvent` (Pydantic) → revisión humana (CSV) → `DecisionEngine` → métricas deterministas (pandas) → Streamlit.

## Reglas inamovibles
1. Código ejecutable en local (CPU) para pruebas pequeñas; el análisis pesado corre en OVHcloud. Ninguna clave de pago es obligatoria para usar el proyecto, y las credenciales nunca van al repositorio.
2. No se guardan nombres (19 oct): cada voz es «Persona 1», «Persona 2»…; en la evidencia y en las transcripciones el nombre se sustituye por el código. El género nunca se infiere de la cara ni de la voz (tampoco del tono). Fuentes permitidas (16 oct): pistas del lenguaje de la transcripción con evidencia («la señora / el señor X»), declarado, registro público o revisión humana; si no, `desconocido` (siempre visible).
3. Las cifras las calcula el código (pandas). El LLM nunca calcula ni resume números.
4. El LLM no tiene herramientas, devuelve JSON cerrado por gramática, validado con Pydantic. Confianza <0,7 → revisión humana. Los datos van delimitados de las instrucciones.
5. Conclusiones solo si la brecha supera el umbral (15 puntos o más, fijado en `docs/metricas.md`), el tiempo sin atribuir es menor que la brecha y el resultado resiste los márgenes de error. Si no: "no concluyente".
6. Cada dato lleva procedencia: `observed`, `computed`, `ai_inferred` o `human_validated`.
7. Nunca se sube al repo audio, vídeo, transcripciones reales ni secretos. Los datos viven fuera (`data/` ignorado).
8. Modelos: usar `nimble` (Apache 2.0), NUNCA `nimble-v3` (CC BY-NC). Jev queda descartado. Kev es experimental (solo inglés). Sin LangChain: motor propio `DecisionEngine` contra una API compatible con OpenAI, agnóstico al modelo.
9. Toda dependencia nueva se anota en `THIRD_PARTY_LICENSES.md` con su licencia verificada en la fuente, no de memoria.
10. Decisiones importantes (licencia, alcance, datos, motores) las aprueba Sabrina antes de implementarse.

## Hardware
Portátiles (CPU, clips cortos) y VM OVHcloud con 2×V100S (Volta: sin bf16; usar float16 o int8, versiones fijadas en el Dockerfile).

## Estructura del repo
`contracts/`, `pipeline/`, `decision/`, `metrics/`, `evaluation/`, `dashboard/`, `tests/`, `docker/`, `docs/`, `THIRD_PARTY_LICENSES.md`, `Makefile`, `.env.example`.

## Cómo trabajar
- Idioma de documentos y mensajes: español. Código y nombres de variables: inglés.
- Cambios pequeños, un PR por tarea, con tests de las métricas y de los contratos.
- Tras cada cambio: `make test` en verde antes de pedir revisión.
- Si algo es ambiguo, elige un valor razonable por defecto, anótalo en el PR y sigue.
- Requisitos y criterios de aceptación: usa los IDs del PRD (RF-xx, RNF-xx, Mxx).

## Requisitos del reto a no olvidar
Repo público dentro de la organización GitHub de la Comunidad IA de Código Abierto; licencia OSI/FSF; README con licencias de terceros y hoja de ruta; pptx de hasta 20 diapositivas; vídeo de 5 minutos; uso de LLM agnóstico al modelo. Puntuación: calidad técnica 30, impacto 15, innovación 15, género 10, open source 10, comunicación 10, ética y normativa 5, despliegue 5.

## Pendiente (29 oct)
El plan completo está en `docs/PLAN_DE_TRABAJO.md` y la especificación del panel en `docs/PANEL.md`.
1. Hacer público el repositorio el 29 oct entre las 23:00 y las 24:00, antes del 30 oct a las 08:00.
2. Cerrar las issues de entrega (#58, #60 y #61).

Fechas límite:
- 30 oct a las 08:00: repositorio público, README y .pptx de 20 diapositivas como máximo.
- Antes del 4 nov a las 08:00: vídeo de 5 minutos y presentación corta.
