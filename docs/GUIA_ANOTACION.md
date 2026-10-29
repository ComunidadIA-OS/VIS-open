# Guía de anotación (para Ivette y Veru)

**Anotar no es transcribir.** El sistema ya transcribe y separa las voces solo. Anotar es **leer lo que ha salido y ponerle una etiqueta** en una hoja de cálculo, para saber cuántas veces acierta. Lo que se anota es la «respuesta correcta» con la que se compara el sistema.

Todas las hojas las prepara el programa a partir de la transcripción automática (con «Persona N» en lugar de nombres). Nadie tiene que escuchar el vídeo entero ni escribir texto desde cero.

## Qué se anota y cuánto

| Qué | Para qué | Cuánto | Quién | Cómo |
|---|---|---|---|---|
| **Preguntas (M09)** | Medir si Qwen detecta bien las preguntas y a quién van dirigidas; y, si hace falta, ajustar Qwen | Piloto: **una pregunta** (~5 min, ~16 turnos). Después, 20 min de una sesión | Ivette | Hoja de turnos: `es_pregunta` (si/no), `frase` y `cargo_destinatario` |
| **Género de 150 turnos** | Medir si el género por lenguaje acierta | **No se hizo:** la sustituyó la lista oficial de intervenciones del Congreso (`docs/EVALUACION.md`, #52) | — | Hoja `turnos_para_anotar.csv`, por si se retoma |
| **Transcripción (WER)** | Medir cuántas palabras falla la transcripción | Un tramo de **2 o 3 minutos** | Ivette | Se parte del texto automático y **se corrigen los errores** (mucho más rápido que escribir). Se puede usar de referencia el Diario de Sesiones |
| **Quién habla cuándo (DER)** | Medir los errores al separar voces | El mismo tramo de 2 o 3 minutos | Ivette | Apuntar los instantes en que cambia quien habla |

Las anotaciones de vídeo de manos levantadas (M14) **ya no hacen falta**: se descartó esa métrica. Las de personas visibles no se hicieron en esta entrega.

## Cuánto es suficiente

- **Una pregunta basta para el piloto:** comprobar que la hoja se entiende y que el formato sirve. No basta para dar una cifra: con unos 16 turnos un solo error mueve mucho el resultado.
- **Para una cifra con sentido** (F1 de las preguntas, ajuste de Qwen) hacen falta más turnos: lo razonable es empezar por los 20 minutos de una sesión y ver cuántos turnos salen. Si salen pocos, se amplía.
- Se anota **solo el bloque de preguntas** de cada sesión (`tramo_inicio` a `tramo_fin` del manifiesto).

## Cómo rellenar la hoja de preguntas

Hoja de ejemplo (una pregunta, 16 turnos): `data/anotacion/ejemplo_una_pregunta.csv`. Columnas:

| Columna | Qué es | Qué pones |
|---|---|---|
| `turn_id`, `t_inicio` | Número de turno y minuto | Nada (ya está) |
| `context_before` | Lo dicho justo antes, para entender | Nada |
| `text` | Lo que dice la persona en ese turno (transcripción automática) | Nada; léelo |
| `es_pregunta` | ¿En este turno se formula una pregunta (con o sin signos de interrogación)? | `si` o `no` |
| `frase` | La frase que formula la pregunta | **Copiada literal** del `text`, o vacío si es `no` |
| `cargo_destinatario` | A quién se dirige, por su cargo | **Copiado literal** del `text` (p. ej. «señora ministra de Hacienda»), o vacío |

Reglas: una afirmación, una exclamación o una cita de lo que preguntó otra persona **no** cuentan como pregunta. Si dudas, `no` y apúntalo aparte. Si el texto automático tiene errores, no lo corrijas en la hoja: copia la frase tal como sale.

**Usa la versión `.xlsx` de la hoja** (columnas separadas, texto ajustado y listas desplegables en `es_pregunta` y `label`). Si solo tienes el `.csv`, **no lo abras con doble clic en Excel** (todo queda en una columna y los acentos se rompen): impórtalo con «Datos > Obtener datos > Desde texto/CSV» eligiendo UTF-8 y coma, o en Google Sheets («Archivo > Importar»). Sabrina genera los `.xlsx` con `python -m evaluation.xlsxio a-xlsx hoja.csv` (PR de las hojas en Excel) y, cuando devuelves la hoja rellena, la pasa a CSV con `a-csv`.

## Qué pasa después

Las hojas anotadas van a Sabrina (no al repositorio: `data/` no se sube). Con ellas se calculan los resultados (`python -m evaluation.questions_eval hoja.csv --engines rules,llm`) y, con una sesión para entrenar y otra distinta para evaluar, el ajuste de Qwen (`docs/M09_PREGUNTAS.md`).
