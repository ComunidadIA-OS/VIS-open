# Roles, bloques de pregunta, M09 y M06

Código que necesitan las métricas de la sesión de control (`docs/metricas.md`, PR de Ivette). Lo escribe Sabrina; Veru lo usa para M02b y para ajustar `metrics/borrador.py`.

## Qué hay

| Pieza | Qué hace |
|---|---|
| `decision/roles.py` | Deduce los **roles** y parte la sesión en **bloques de pregunta** |
| `decision/questions.py` | Detector de preguntas (reglas o Qwen). Nuevo: `cargo_destinatario`, siempre cita literal |
| `metrics/m09.py` | **M09** (preguntas recibidas, normalizada, Presidente del Gobierno aparte) y **M06** |

```bash
python -m decision.roles data/processed/<sesión>/timeline.json     # escribe bloques_pregunta.json
python -m metrics.m09 data/processed/<sesión>/timeline.json --engine llm
```

## Cómo se deducen los roles

En el bloque de preguntas del Pleno cada pregunta sigue el mismo guion: la Presidencia da la palabra, habla quien pregunta, responde un miembro del Gobierno, y vuelven réplica y dúplica.

1. **PRESIDENCIA:** la voz que más veces dice una fórmula de dar la palabra («tiene la palabra…») o de anunciar una pregunta («Pregunta del diputado don…», «La siguiente pregunta la formula la diputada doña…»), si lo hace al menos dos veces (`decision/cues/es.toml`). Se excluye de las métricas salvo M13.
2. Si la Presidencia anuncia las preguntas (sesión de control), cada **anuncio** abre un **bloque** (una pregunta, con su número); «tiene la palabra» ahí se usa también para la réplica y no abre bloque. Si no hay anuncios (otros debates), cada vez que da la palabra empieza un bloque. Comprobado con los Diarios de Sesiones: 20, 19 y 17 anuncios el 19/09/2018, 05/10/2022 y 30/09/2026, igual que las preguntas del orden del día.
3. **PREGUNTA:** la primera voz que habla en el bloque. **GOBIERNO:** la primera voz distinta que le contesta. Las voces que hablan menos de 1 s se ignoran, y las intervenciones seguidas de la misma voz a menos de 1 s forman un turno.
4. El rol es **de cada bloque**, no de cada persona (un ministro que también es diputado puede preguntar y responder). `Speaker.role` guarda el que más veces tiene.

`QuestionBlock` da a las métricas: nº de pregunta (para M02b), quién pregunta, quién responde, los turnos con sus segundos (para M02b y M03) y el texto de quien pregunta (para Qwen).

## M09 y M06 (según Ivette)

- **Destinataria = quien responde** en el bloque (lo decide el código por el orden de las voces). El `cargo_destinatario` de Qwen solo separa las preguntas al **Presidente del Gobierno** (van aparte y no entran en b) y sirve de contraste.
- **a)** preguntas recibidas por persona y género; **b) normalizada:** tasa por ministra / tasa por ministro (valor de M09; 1 = igualdad); **c)** Presidente del Gobierno aparte.
- Confianza < 0,7: no se cuenta y se lista en `pendientes_de_revision`.
- Muestra mínima (apartado 4 ter): 4 voces con género conocido y 600 s; si no, «no concluyente: muestra insuficiente». Siempre va la nota de la variable de confusión (la actualidad de cada ministerio).
- **M06:** % de las preguntas al Presidente del Gobierno que formulan mujeres; descriptiva por sesión.
- Qwen devuelve `is_question`, `confidence`, `evidence` (cita literal), `cargo_destinatario` (cita literal o null) y `reason`. Un cargo que no está en el texto se descarta; el texto va delimitado como dato y no hay herramientas.

## Límites

- Depende de que la diarización separe bien las voces y de que la Presidencia diga la fórmula de dar la palabra; si no la encuentra, no hay bloques (y las métricas salen «no concluyentes»).
- Las sesiones V001 a V004 **no son de control** (V004 es un debate de un real decreto): sirven para comprobar que el código corre, no para sacar cifras. Las de verdad son V005 a V007.
- Pendiente de comprobar con las sesiones reales: cuántos bloques salen frente al orden del día, y el error de roles con la anotación manual.
- M02b (uso del tiempo asignado) lo programa Veru con `QuestionBlock.turns`: el tiempo asignado es de 5 minutos por pregunta repartidos a partes iguales entre quien pregunta y quien responde, es decir, 150 s cada uno (art. 188.3 del Reglamento del Congreso y Resolución de la Presidencia de 10 de junio de 2008, texto consultado el 22 oct 2026). La tolerancia de 10 s es de Ivette.
