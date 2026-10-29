# MEMORY.md · Memoria del proyecto

Hechos y decisiones que una sesión nueva no debe volver a preguntar. Una línea por hecho; actualiza en vez de duplicar. Sin secretos.

## Proyecto
- Reto "Mujeres por la IA Abierta" (SEDIA / Comunidad IA de Código Abierto). Bases: https://github.com/ComunidadIA-OS/Reto-de-Mujeres-por-la-IA-abierta
- Entregas: antes del 30 oct 2026 a las 08:00 (hora de Madrid), repositorio público con README y presentación .pptx (máximo 20 diapositivas); antes del 4 nov a las 08:00, vídeo de 5 minutos (la Organización lo permite hasta esa fecha) y versión corta del .pptx (5 minutos con demo). Cierre del código: 28 oct.
- Falta de un entregable en plazo = exclusión de la evaluación.
- Contacto del reto: comunidad.ia.os@digital.gob.es; mentoras en Discord #reto-mujeres-ia-abierta.
- Repositorio en la organización de la Comunidad: https://github.com/ComunidadIA-OS/VIS-open (acceso ya resuelto; aún privado).

## Equipo
- Sabrina (dirección, arquitectura, pipeline de IA, modelo de lenguaje, infraestructura, publicación y vídeo), Ivette (define y valida las métricas, sin programar; presentación .pptx), Veru (datos, programa las métricas, panel, plan de puesta en producción, revisión del repositorio).
- Cada persona dispone de unas 2 h por día laborable; los fines de semana no se cuentan.

## Plan de la entrega (19 oct)
- Plan detallado en `docs/PLAN_DE_TRABAJO.md`.
- 3 sesiones del Congreso. Métricas de esta entrega: M01, M02, M03, M04, M13, M14 (vídeo) y M09 (IA). El resto es evolución futura.
- Ajuste ligero de Qwen (28 oct) con medición antes y después; si no mejora, se conserva el modelo sin ajustar. Datos (19 oct): texto de nuestra transcripción de una sesión con preguntas anotadas por Ivette, comprobado con el Diario de Sesiones; evaluación con otra sesión; el modelo ajustado no se publica.
- Para M09 se puede usar Qwen a través de OVH AI Endpoints (API compatible con OpenAI); el sistema sigue siendo agnóstico al modelo.

## Decisiones tomadas
- Fuente: solo sesiones del Congreso, sin modificar; los vídeos nunca van al repo. Descarga manual por ahora; la automática es evolución futura.
- Sin nombres (19 oct): cada voz se identifica con un código anónimo (Persona 1, Persona 2…); en la evidencia y en las transcripciones el nombre se sustituye por el código.
- Género (16 oct): nunca por cara ni voz. Se asigna por pistas del lenguaje («la señora / el señor X»), con evidencia; si no, `desconocido` y revisión humana. Pendiente del visto bueno de Ivette.
- El vídeo (manos levantadas) forma parte del producto, sin reconocimiento facial.
- Jev: no usar. Kev: experimental (solo inglés). `nimble` sí (Apache 2.0); `nimble-v3` no (CC BY-NC 4.0).
- Sin LangChain; `DecisionEngine` propio, `RulesEngine` por defecto.
- Licencia del repo: Apache-2.0 (aprobada).

## Estado (20 oct 2026)
- Hecho: el pipeline completo funciona en el notebook de OVH del equipo (2 GPU V100S, `sm_70` correcto, `docs/PRUEBA_GPU.md`). Una sesión de 1 h 19 min se analiza en 7 min 22 s y separa 12 voces; 8 reciben género por pistas del lenguaje.
- Hecho: seudonimización («Persona N», modo estricto), métricas M01–M04 y M13 en borrador, panel Streamlit, módulo de vídeo sin cara (`pipeline/video.py`, falta probarlo con el modelo de pose), evaluación (`docs/EVALUACION.md`) y costes (`docs/COSTES_API.md`).
- Hecho: AI Endpoints de OVH conectado con Qwen3.5-9B; con `reasoning_effort: none` baja a 63 tokens de salida y 3,6 s por llamada (0,000044 € por llamada).
- Pendiente de otras personas: tres sesiones de años distintos, definiciones formales de las métricas (también M09), revisión de la regla de género, anotación de 150 turnos y de un tramo de vídeo (Ivette); revisión del repositorio el 29 oct (Veru).
- Pendiente: probar el vídeo en OVH, M09, ajuste ligero de Qwen (28 oct), WER y DER, publicar el repositorio (29 oct) y el vídeo de 5 minutos.
- Presentaciones: citar la fuente de cada sesión (Congreso de los Diputados, órgano, fecha, «vídeo sin alterar» y fecha de última consulta), el aviso legal del Congreso y las licencias de terceros. La consulta legal a la Organización y los formularios de consentimiento son opcionales.

## Para la presentación (lo que Sabrina pide que aparezca)
- Innovación y accesibilidad (21 oct): asistente de voz de lista cerrada, validación Human in the loop por voz, modo manos libres con detector de voz propio (rechaza teclas, tráfico, bocinas y el audio del vídeo), subtítulos para sordos, lector de pantalla. Todo en local salvo la transcripción de órdenes y Qwen en OVH. Datos en `docs/PROVEEDORES.md`; límites en `docs/DECLARACION_ACCESIBILIDAD.md`.
- Término literal «Human in the loop»: el panel pide confirmar a dos anotadoras el género de las voces `desconocido`, viendo el vídeo y la transcripción; solo cuenta si coinciden dos personas (procedencia `anotacion_percibida`).
- El género nunca sale del sonido ni de la cara: pyannote solo separa voces; el género sale del texto (pistas del lenguaje) o de la confirmación humana. MediaPipe solo da puntos del cuerpo (presencia, tiempo en pantalla, manos); el género en pantalla se hereda de la voz.
- Panel: vídeo a la izquierda, transcripción (con ▶ a cada minuto) y Human in the loop a la derecha; cambio de vídeo arriba a la derecha; responsive (escritorio y móvil); letra grande para proyectar.
- Informe de análisis de audio, vídeo y consumo (tokens y euros) con `python -m evaluation.informe`; WER y DER (`evaluation/asr_diar.py`).
- Límites del vídeo: modelo de pose de una sola persona (Apache-2.0), cuenta de menos en planos amplios.
- Todo open source y en local. Para producción (`docs/PRODUCCION.md`): usuario, contraseña y 2FA, base de datos compartida (PostgreSQL), automatización de sesiones nuevas.

- Regla de género confirmada por Sabrina (20 oct): «dar la palabra a la señora/el señor = mujer/hombre» vale para todos los vídeos, incluso con voces fusionadas por la diarización (`split_on_floor_grant`); pendiente del visto bueno de Ivette.

## Reglas de trabajo
- El género nunca se infiere de la cara ni de la voz; `desconocido` siempre visible.
- Ningún secreto (tokens, `.env`) ni dato real (vídeos, audios, transcripciones) en el repositorio ni en carpetas que lea la organización.
- Un cambio por rama y por PR; los conflictos de `CHANGELOG.md` se resuelven aceptando ambos cambios.
- Los CSV no se abren con doble clic en Excel (rompe las tildes y las columnas).

## Pendiente
- Verificar en la fuente las licencias del modelo de pose de MediaPipe y de Qwen.
- Confirmar si el Congreso permite la descarga automática (evolución futura).
- Confirmar la licencia del corpus Àgora (evolución futura).
