# Cómo contribuir a VIS Open

VIS Open es el proyecto del Equipo 6 para el reto "Mujeres por la IA Abierta" (SEDIA, Comunidad IA de Código Abierto). Lee primero `README.md` y `CLAUDE.md`. Este documento sigue los términos y condiciones del reto (arts. 7, 9, 10, 12, 16 y 17).

## Contexto del reto

- El repositorio es público y se publica bajo una licencia de código abierto reconocida por la OSI (aquí, Apache-2.0). Debe vivir en la organización de GitHub de la Comunidad IA de Código Abierto.
- Solo se evalúa el código desarrollado desde la apertura oficial del reto (14 de octubre de 2026) hasta la entrega (30 de octubre de 2026, 08:00).
- Cada equipo presenta un único proyecto y lo forman tres integrantes. Hasta que termine la evaluación, el código lo escriben ellas. Las propuestas externas se reciben como issues; cualquier contribución externa de código se estudia después, y se acepta bajo la licencia del proyecto.

## Flujo de trabajo

1. Abre una issue (hito, error o propuesta) antes de un cambio grande.
2. Crea una rama desde `main`: `m2-pipeline`, `fix-csv-columnas`, etc.
3. Haz commits pequeños y descriptivos, en imperativo: "Añade lectura del CSV de revisión".
4. Antes de abrir la PR, ejecuta `make check` (lint y tests). La CI hace lo mismo.
5. Abre una PR que explique qué cambia y por qué. Otra integrante del equipo la revisa antes de fusionar.

## Qué hacer cuando falta algo

| Si falta o falla… | Qué hacer |
|---|---|
| Un error o un resultado raro | Abre una issue con pasos para reproducirlo (con datos sintéticos, nunca reales). Si sabes arreglarlo, abre una PR que la cierre. |
| Una función o métrica nueva | Abre una issue explicando para qué sirve y cómo se mide. Las métricas las valida Ivette antes de implementarse. |
| Documentación (README, `docs/`, docstrings) | Edítala tú misma en una PR pequeña. No hace falta issue previa. |
| Un test | Añádelo en `tests/` con datos sintéticos. Todo cambio de comportamiento lleva su test. |
| Una dependencia o su licencia | Añade la fila a `THIRD_PARTY_LICENSES.md`, con la licencia verificada en la fuente, en la misma PR que la usa. |
| Un dato del PRD o una decisión | Pregúntalo en una issue. Las decisiones importantes (licencia, modelos, alcance) las aprueba Sabrina. |
| Algo que no sabes dónde encaja | Abre una issue con la etiqueta `pregunta`. Mejor preguntar que adivinar. |

Para proponer una contribución nueva (una mejora, un modelo abierto, un caso de uso): abre una issue, espera una respuesta de alguien del equipo, trabaja en una rama y abre una PR enlazando la issue ("Cierra #N").

## Reglas del proyecto

- **Género:** nunca se infiere de la cara ni de la voz. Sale de pistas del lenguaje de la transcripción, de un dato declarado o de la revisión humana, y el informe dice cómo se obtuvo; `desconocido` siempre es visible.
- **Sin reconocimiento facial.**
- **Datos:** no se suben al repo audio, vídeo, transcripciones reales ni datos personales. Los tests usan solo datos sintéticos. Tratar datos personales reales exige base jurídica y autorización expresa de la Organización (art. 12.3).
- **Secretos:** nunca en el repo, en issues ni en PRs (tokens de OVHcloud o de Hugging Face, claves, PDF de acceso). Van en `.env`, que está ignorado. Las credenciales no se comparten con personas ajenas al equipo.
- **Dependencias:** cada una se añade a `THIRD_PARTY_LICENSES.md` con su licencia verificada en la fuente y compatible con la del proyecto. El software preexistente debe identificarse con claridad (art. 17).
- **Modelos de lenguaje:** el motor de decisión es agnóstico del modelo y se conecta por una API compatible con OpenAI. Se prefieren modelos abiertos (art. 10).
- **Infraestructura cedida:** se usa solo para el reto, sin minería de criptoactivos, escaneos ni servicios abiertos a terceros (art. 12.3). Las V100S no admiten bf16: se usa float16 o int8 (Anexo I).
- **Autoría y derechos:** quien contribuye declara que tiene los derechos sobre lo que aporta y que no infringe derechos de terceros (art. 16).

## Estilo

Python 3.11 o superior, `ruff` con línea de 100 caracteres, esquemas con Pydantic, comentarios y docstrings en español.

## Conducta

Al participar aceptas el [código de conducta](CODE_OF_CONDUCT.md).
