# CLAUDE.md · Mujeres por la IA Abierta

Instrucciones para cualquier sesión de Claude Code que trabaje en este repositorio. Lee también `MEMORY.md` y `SKILLS.md`.

## Qué es
Herramienta abierta y local que mide, a partir del audio y el vídeo de debates (sin reconocimiento facial), la presencia, participación, protagonismo y representación de las mujeres. Reto "Mujeres por la IA Abierta" (SEDIA / Comunidad IA de Código Abierto).
Entrega oficial: 30 oct 2026 08:00. Cierre del equipo: 28 oct. Presentación presencial: 4 nov.

## Estado: M1 y M2 hechos; en curso el trabajo del prompt M3 (17 oct 2026)
- M1 (hecho) = estructura del repo, esquemas Pydantic (`contracts/`), CI, `make test` y `THIRD_PARTY_LICENSES.md`.
- M2 (hecho, rama `m2-pipeline`) = audio, transcripción, diarización, línea de tiempo y CSV de revisión.
- Siguiente (prompt M3, una rama por bloque): Docker y prueba en GPU, fuente Congreso y manifiesto, género por lenguaje, marco de métricas, motores de decisión y datos sintéticos. Las métricas M01 a M13 y sus umbrales siguen siendo de Ivette.
- Licencia Apache-2.0 aprobada por Sabrina (16 oct 2026); falta comunicarla a Ivette y Veru.
- El vídeo (gestos de levantar la mano) está en el MVP y no se propone como opcional; sin reconocimiento facial.
- Fuente del MVP (16 oct): solo sesiones del Congreso, sin modificar ni alterar el vídeo; los vídeos nunca van al repo ni se usan para entrenar.
- Infra: desarrollo y pruebas pequeñas en local (CPU); transcripción, diarización y LLM en las VM de OVHcloud (2 espacios, 2×V100S cada uno; Volta: float16/int8, sin bf16). OVH se usa de forma prioritaria. Credenciales nunca en el repo.
- Documentos de referencia: propuesta de arquitectura y PRD (enlaces en `MEMORY.md`).
- Las métricas (sección 5 del PRD) son un borrador hasta el visto bueno de Ivette.

## Equipo y propiedad
- Sabrina: dirección, arquitectura, pipeline de IA, infraestructura, RGPD y AI Act.
- Ivette (2 h/día): métricas y validación, libro de códigos de anotación.
- Veru: datos, ética y género, dashboard, landing y guion del vídeo.
Cada carpeta tiene una persona responsable; los cambios en carpetas ajenas se proponen por PR.

## Arquitectura en una línea
vídeo → audio (FFmpeg) + gestos (OpenCV/MediaPipe) → faster-whisper + WhisperX → pyannote → línea de tiempo `AnalysisEvent` (Pydantic) → revisión humana (CSV) → `DecisionEngine` → métricas deterministas (pandas) → Streamlit.

## Reglas inamovibles
1. Todo en local. Sin servicios en la nube ni claves de pago obligatorias.
2. El género nunca se infiere de la cara ni de la voz (tampoco del tono). Fuentes permitidas (16 oct): pistas del lenguaje de la transcripción con evidencia («la señora / el señor X»), declarado, registro público o revisión humana; si no, `desconocido` (siempre visible).
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
