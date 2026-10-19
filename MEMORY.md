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

## Estado (19 oct 2026)
- M1, M2 y los bloques A a G de M3 están unidos en `main`. `pipeline.run` encadena transcripción, diarización, género por lenguaje y `resumen.json`.
- Pendiente: prueba real en la GPU de OVH, métricas definitivas, panel, M09 y ajuste del modelo.

## Pendiente
- Verificar en la fuente las licencias de OpenCV, MediaPipe, Streamlit y Qwen.
- Confirmar si el Congreso permite la descarga automática (evolución futura).
- Confirmar la licencia del corpus Àgora (evolución futura).
