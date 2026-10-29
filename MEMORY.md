# MEMORY.md · Memoria del proyecto

Hechos y decisiones que una sesión nueva no debe volver a preguntar. Una línea por hecho; actualiza en vez de duplicar. Sin secretos.

## Proyecto
- Reto "Mujeres por la IA Abierta" (SEDIA / Comunidad IA de Código Abierto). Bases: https://github.com/ComunidadIA-OS/Reto-de-Mujeres-por-la-IA-abierta
- Entregas: antes del 30 oct 2026 a las 08:00 (hora de Madrid), repositorio público con README y presentación .pptx (máximo 20 diapositivas); antes del 4 nov a las 08:00, vídeo de 5 minutos (la Organización lo permite hasta esa fecha) y versión corta del .pptx (5 minutos con demo). Cierre del código: 28 oct.
- Falta de un entregable en plazo = exclusión de la evaluación.
- Contacto del reto: comunidad.ia.os@digital.gob.es; mentoras en Discord #reto-mujeres-ia-abierta.
- Repositorio en la organización de la Comunidad: https://github.com/ComunidadIA-OS/VIS-open (acceso ya resuelto; privado hasta el 29 oct, que se hace público entre las 23:00 y las 24:00).

## Equipo
- Sabrina (arquitectura e integración, pipeline de IA, panel, infraestructura, RGPD y AI Act, plan de puesta en producción, vídeos, presentación del 04.11 y publicación), Ivette (definición y validación de métricas, evaluación del modelo, revisión del código, del panel y de la seudonimización, presentación .pptx) y Veru (programación de las métricas).
- Cada persona dispone de unas 2 h por día laborable; los fines de semana no se cuentan.

## La entrega (29 oct)
- Plan detallado en `docs/PLAN_DE_TRABAJO.md`.
- 3 sesiones del Congreso: V005 (30/09/2026), V006 (05/10/2022) y V007 (19/09/2018). Métricas de esta entrega: M01, M02 (con M02b), M03a, M03b, M04, M06, M09 y M13 (`docs/metricas.md`). Descartadas para el Congreso: M05, M08, M10 y M14–M16. El resto es evolución futura.
- Ajuste ligero de Qwen: queda en la hoja de ruta, con la sesión de desarrollo V008 (21/09/2022); si no mejora, se conserva el modelo sin ajustar. El modelo ajustado no se publica.
- Para M09 se puede usar Qwen a través de OVH AI Endpoints (API compatible con OpenAI); el sistema sigue siendo agnóstico al modelo.

## Decisiones tomadas
- Fuente: solo sesiones del Congreso, sin modificar; los vídeos nunca van al repo. Detección y descarga de plenos nuevos con `pipeline.sesion --buscar` y análisis con `--pendientes` (`docs/FLUJO.md`), con validación humana antes del análisis.
- Sin nombres (19 oct): cada voz se identifica con un código anónimo (Persona 1, Persona 2…); en la evidencia y en las transcripciones el nombre se sustituye por el código.
- Género (16 oct): nunca por cara ni voz. Se asigna por pistas del lenguaje («la señora / el señor X»), con evidencia; si no, `desconocido` y revisión humana. Validada por Ivette (25–27 oct) frente a la lista oficial de intervenciones (`docs/EVALUACION.md`).
- El vídeo (manos levantadas) forma parte del producto, sin reconocimiento facial.
- Jev: no usar. Kev: experimental (solo inglés). `nimble` sí (Apache 2.0); `nimble-v3` no (CC BY-NC 4.0).
- Sin LangChain; `DecisionEngine` propio, `RulesEngine` por defecto.
- Licencia del repo: Apache-2.0 (aprobada).
- Responsable del tratamiento en el reto: el Equipo 6 (Sabrina, Ivette y Veru), las tres por igual, sin jerarquía (29 oct; `docs/PRODUCCION_RGPD_AIACT.md`).
- Retención propuesta para producción (29 oct): vídeo borrado tras validar el informe, como máximo a los 30 días; de las anotadoras, durante 12 meses solo el género acordado y sus códigos seudónimos (arts. 5.1.c y 5.2 RGPD).
- En la documentación no se usa la palabra «borrador» (29 oct).

## Estado (29 oct 2026)
- Hecho: el pipeline completo funciona en el notebook de OVH del equipo (2 GPU V100S, `sm_70` correcto, `docs/PRUEBA_GPU.md`), con las 3 sesiones de evaluación procesadas.
- Hecho: seudonimización («Persona N», modo estricto), métricas de la entrega con las definiciones de Ivette, panel Streamlit con Human in the loop, asistente de voz y manos libres (beta), vídeo sin cara, evaluación (`docs/EVALUACION.md`) y costes (`docs/HERRAMIENTAS_Y_COSTES.md`).
- Hecho: AI Endpoints de OVH conectado con Qwen3.5-9B para M09 y el resumen.
- Hecho: validación de Ivette (25–27 oct) frente a la lista oficial de intervenciones: 87/87 personas, 86 con el género correcto, 0 errores y 1 a revisión humana; M06 en 3 de 3 sesiones y M09 en 2 de 3.
- Hecho: plan de puesta en producción (`docs/PRODUCCION.md` y `docs/PRODUCCION_RGPD_AIACT.md`), vídeo explicativo y presentaciones (completa y corta) en Releases. Auditoría del historial (29 oct): sin secretos, sin audio ni vídeo reales y sin nombres.
- Pendiente: hacer público el repositorio (29 oct, 23:00–24:00) y cerrar las issues de entrega. Hoja de ruta: ajuste ligero de Qwen, DER y WER exacto con un tramo anotado a mano (el WER aproximado frente al Diario de Sesiones es 10,0 %, cota superior).
- Presentaciones: citar la fuente de cada sesión (Congreso de los Diputados, órgano, fecha, «vídeo sin alterar» y fecha de última consulta), el aviso legal del Congreso y las licencias de terceros. La consulta legal a la Organización y los formularios de consentimiento son opcionales.

## Para la presentación (lo que Sabrina pide que aparezca)
- Innovación y accesibilidad (21 oct): asistente de voz de lista cerrada, validación Human in the loop por voz, modo manos libres con detector de voz propio (rechaza teclas, tráfico, bocinas y el audio del vídeo), subtítulos para sordos, lector de pantalla. Todo en local salvo la transcripción de órdenes y Qwen en OVH. Datos en `docs/PROVEEDORES.md`; límites en `docs/DECLARACION_ACCESIBILIDAD.md`.
- Término literal «Human in the loop»: el panel pide confirmar a dos anotadoras el género de las voces `desconocido`, viendo el vídeo y la transcripción; solo cuenta si coinciden dos personas (procedencia `anotacion_percibida`).
- El género nunca sale del sonido ni de la cara: pyannote solo separa voces; el género sale del texto (pistas del lenguaje) o de la confirmación humana. MediaPipe solo da puntos del cuerpo (presencia, tiempo en pantalla, manos); el género en pantalla se hereda de la voz.
- Panel: vídeo a la izquierda, transcripción (con ▶ a cada minuto) y Human in the loop a la derecha; cambio de vídeo arriba a la derecha; responsive (escritorio y móvil); letra grande para proyectar.
- Informe de análisis de audio, vídeo y consumo (tokens y euros) con `python -m evaluation.informe`; WER y DER (`evaluation/asr_diar.py`).
- Límites del vídeo: modelo de pose de una sola persona (Apache-2.0), cuenta de menos en planos amplios.
- Todo open source y en local. Para producción (`docs/PRODUCCION.md`): usuario, contraseña y 2FA, base de datos compartida (PostgreSQL), automatización de sesiones nuevas.

- Regla de género confirmada por Sabrina (20 oct): «dar la palabra a la señora/el señor = mujer/hombre» vale para todos los vídeos, incluso con voces fusionadas por la diarización (`split_on_floor_grant`); validada por Ivette (25–27 oct).

## Reglas de trabajo
- El género nunca se infiere de la cara ni de la voz; `desconocido` siempre visible.
- Ningún secreto (tokens, `.env`) ni dato real (vídeos, audios, transcripciones) en el repositorio ni en carpetas que lea la organización.
- Un cambio por rama y por PR; los conflictos de `CHANGELOG.md` se resuelven aceptando ambos cambios.
- Los CSV no se abren con doble clic en Excel (rompe las tildes y las columnas).

## Pendiente
- Confirmar si el Congreso permite la descarga automática (evolución futura).
- Confirmar la licencia del corpus Àgora (evolución futura).
