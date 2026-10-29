# Métricas · Equipo 6, VIS Open

Definiciones formales de las métricas de esta entrega. Definiciones de Ivette, validadas con la lista oficial de intervenciones del Congreso (25–27 oct 2026, `docs/EVALUACION.md`).

## 1. Contexto: qué analizamos

- **Unidad de análisis:** el bloque de preguntas de una sesión de control al Gobierno del Congreso de los Diputados (tramo_inicio a tramo_fin del manifiesto).
- **Sesiones:** V005 (XV, sesión plenaria 202, miércoles 30/09/2026; el orden del día se publica como «pleno_201» porque cubre toda la semana desde el martes, que es la sesión 201), V006 (XIV, 05/10/2022) y V007 (XII, 19/09/2018).
- **Por qué este formato:** es comparable entre años, tiene referencia oficial (orden del día y Diario de Sesiones) y los turnos están ordenados, lo que facilita separar las voces.
- **Limitación importante:** en la sesión de control el tiempo de cada pregunta está fijado por el Reglamento. Las diferencias de tiempo entre mujeres y hombres vienen sobre todo de **cuántas veces** habla cada grupo, no de cuánto dura cada intervención. Por eso las métricas ponen el foco en el reparto de oportunidades: quién pregunta, a quién se pregunta y quién ocupa los turnos más visibles.

## 2. Reglas comunes a todas las métricas

| Regla | Definición |
|---|---|
| Roles | Cada persona tiene un rol: `PRESIDENCIA` (quien preside), `PREGUNTA` (diputada o diputado que formula) o `GOBIERNO` (quien responde). |
| Presidencia | Se excluye de todas las métricas salvo M13. Se informa aparte. |
| Género | `mujer`, `hombre` o `desconocido`, atribuido por pistas del lenguaje («la señora», «el señor», «la ministra»). La IA nunca lo infiere de la voz ni de la cara. Se informa como género atribuido, no autodeclarado, y binario (más `desconocido`). |
| Desconocido y sin atribuir | Igual que en el código (`metrics/frame.py`): `desconocido` es una voz identificada sin pista de género; `sin_atribuir` es tiempo de voz que no se ha asignado a ninguna voz. Los dos se muestran siempre aparte y nunca se reparten entre mujeres y hombres. |
| Muestra mínima | Cada métrica fija dos mínimos, que usa el marco de código: voces con género conocido y segundos con género conocido (apartado 4 ter). Además, para comparar dos grupos hacen falta al menos 2 voces en cada uno. Si no se cumple, el resultado es «no concluyente: muestra insuficiente». |
| Margen de error | En las métricas de tiempo, el margen es la parte del tiempo que no sabemos atribuir (desconocido + sin atribuir, en puntos de %): es lo máximo que podría moverse el resultado si todo ese tiempo fuera de un solo grupo. |
| Cálculo | Lo hace siempre el código (pandas) sobre la línea de tiempo. La IA solo clasifica turnos en M09. |
| Preguntas válidas | Solo las formuladas en la sesión. Las aplazadas o retiradas según el orden del día no cuentan. |

## 2 bis. Decisiones de diseño y por qué

| Decisión | Por qué |
|---|---|
| Analizar solo el bloque de preguntas de la sesión de control | Mismo formato en los tres años (comparable), referencia oficial para validar (orden del día y Diario), turnos ordenados y casi sin solapamientos, y coste de cómputo asumible. Limitación: no representa todo el Congreso; otros formatos quedan como evolución futura |
| Tres sesiones iguales en todo menos en el año | Si solo cambia el año, las diferencias se deben al paso del tiempo y no al formato. Criterios: sesión de control ordinaria, legislaturas distintas, misma época del año, número de preguntas parecido y documento oficial de referencia |
| Separar quien pregunta (diputadas y diputados) de quien responde (Gobierno) | Son decisiones distintas, tomadas por personas distintas y en momentos distintos. Quién pregunta lo decide cada grupo parlamentario en cada sesión: mide si los grupos dan la palabra a sus diputadas. Quién responde lo decidió la Presidencia del Gobierno al nombrar ministros: mide la composición del Gobierno. Mezclarlos oculta lo que se quiere medir. Ejemplo (sesión de 2018): preguntan 10 mujeres y 10 hombres (paridad); las ministras responden 13 preguntas y los ministros 7. Juntos darían un 58 % de mujeres, que reflejaría la composición del Gobierno y no el reparto de la palabra entre diputadas y diputados. Se separa por el rol en cada intervención, no por tener escaño, porque muchos miembros del Gobierno también son diputados |
| Presidencia de la Cámara aparte | Da la palabra en todas las preguntas: su tiempo no refleja protagonismo y distorsionaría todas las métricas |
| Quien encabeza el Gobierno, aparte en M09 b) y en M06 | Recibe varias preguntas fijas por su cargo. Si la Presidencia del Gobierno no comparece, ocupa su lugar la Vicepresidencia Primera |
| Composición de la cámara calculada de dos maneras (A y B) | Para medir el error de usar la aproximación por legislatura y decidir con datos si el dato de cada día es necesario (apartado 4 bis) |
| La IA solo clasifica; las cifras las calcula el código | Transparencia y reproducibilidad: cualquier persona puede repetir el cálculo |
| El género se atribuye por el lenguaje, nunca por la voz o la imagen | Marco ético del proyecto (RNF-05 y RNF-13) y sesgos conocidos de esos sistemas |
| M03a/M03b cuentan intervenciones y voces, no pausas | La regla anterior (pausa de menos de 1 s) partía cada intervención con los aplausos o rumores: daba 6,7 / 8,9 / 7,1 frente a 3,9 / 3,8 / 3,8 oficiales. Ahora se cuenta por cambio de voz, ignorando los tramos de otra voz de menos de 5 s. El resultado varía menos de 0,2 entre 1 y 5 s, y 5 s es el umbral que mejor equilibra M03a y M03b (apartado 4, M03). Decisión de Ivette, 25/10/2026; cifras recalculadas el 26/10/2026 con los ficheros regenerados |

## 3. Regla para sacar conclusiones

Una frase del tipo «las mujeres tienen menos protagonismo» solo aparece en el informe si se cumplen las tres condiciones:

1. La brecha de M04, **en valor absoluto**, es de **15 puntos o más** (15,0 cuenta como brecha; −18 cuenta como 18).
2. El tiempo sin atribuir (M13) es **menor del 20 %** y **menor que la brecha** (es el margen de error).
3. Se cumple la muestra mínima.

Si falla alguna, el panel muestra «no concluyente» y explica cuál. En el código, esta regla la aplica `gap_is_conclusive` (`metrics/registry.py`), con el umbral de 15 puntos que se fija aquí.

**Por qué 15 puntos.** Es un umbral de prudencia fijado de antemano, no un resultado estadístico. Sale del tamaño de la muestra: una sesión de control tiene entre 17 y 20 preguntas, así que una sola pregunta mueve M04 c) unos 5 o 6 puntos (1 de 17 = 5,9). Con 15 puntos, la diferencia tiene que ser de al menos unas tres preguntas, no de una o dos que podrían deberse a un error de atribución o a la casualidad del orden del día. Con las tres sesiones actuales ninguna brecha llega a 15 (la mayor es +13,9, en M04 c) de 2026), así que todas son «no concluyente»; por eso el panel enseña siempre la cifra y no solo la etiqueta. Es un parámetro del código: con más sesiones se podrá sustituir por un intervalo de confianza.

## 4. Métricas de esta entrega

M01, M02 (con la submétrica M02b), M03a, M03b, M04, M06, M09 y M13.

### M01 · Presencia

| Campo | Contenido |
|---|---|
| Pregunta | ¿Cuántas mujeres y cuántos hombres intervienen, y con qué rol? |
| Tipo | Determinista |
| Entrada | persona_id, género, rol |
| Fórmula | Número de persona_id distintas por género y rol |
| Unidad | Personas y % sobre el total de personas del mismo rol |
| Salida | Tabla rol × género (PREGUNTA y GOBIERNO) |
| Casos límite | Una misma persona separada en dos voces por error cuenta dos veces: se revisa con M03a/M03b y con la anotación manual |
| Validación | Comparar con el orden del día (quién pregunta) y el Diario de Sesiones (quién responde) |
| Test | 3 voces: P1 mujer PREGUNTA, P2 hombre GOBIERNO, P3 mujer GOBIERNO → PREGUNTA: 1 mujer; GOBIERNO: 1 mujer, 1 hombre |

### M02 · Tiempo de palabra

| Campo | Contenido |
|---|---|
| Pregunta | ¿Cuánto tiempo habla cada grupo? |
| Tipo | Determinista |
| Entrada | inicio, fin, persona_id, género, rol |
| Fórmula | Tiempo = suma de (fin − inicio) por persona. % = tiempo del grupo / tiempo atribuido total (sin Presidencia ni desconocido) |
| Unidad | Segundos y % |
| Salida | Por persona, por género y por género × rol. También tiempo medio por persona de cada grupo |
| Interpretación | El tiempo por intervención está reglado: una diferencia grande indica sobre todo diferencia en el número de intervenciones |
| Diferencia mujeres − hombres | 2 × M02 − 100, en puntos, sobre el tiempo con género conocido (como M02). Si hay tiempo sin género, el Resumen del panel da además el intervalo posible según cómo fueran esas voces (2022: entre −10,6 y −5,6). Descriptiva y sin umbral: la regla de conclusiones (apartado 3) usa M04, que tiene en cuenta cuántas mujeres intervienen. Ejemplo (2018): las mujeres hablan 12,7 puntos más que los hombres, pero M04 a) es −1,7, porque son el 58 % de quienes intervienen |
| Muestra mínima | Para publicar la cifra: 4 voces con género conocido y 300 s (apartado 4 ter). Para comparar mujeres y hombres (lo que hacen M02b y M04): además, al menos 2 voces en cada grupo |
| Validación | Error ≤ 3 puntos en el % de tiempo de mujeres frente a la anotación manual de 20 min |
| Test | P1 mujer 0–10 s, P2 hombre 10–15 s → mujeres 10 s (66,7 %), hombres 5 s (33,3 %) |

#### M02b · Uso del tiempo asignado (submétrica de M02)

| Campo | Contenido |
|---|---|
| Pregunta | ¿Quién agota o sobrepasa el tiempo que le corresponde? Sobrepasarlo es ocupar espacio, una señal de protagonismo |
| Tipo | Determinista |
| Contexto | Cada pregunta dispone de unos 5 minutos: unos 150 s para quien pregunta (pregunta + réplica) y unos 150 s para quien responde (respuesta + dúplica) |
| Entrada | inicio, fin, persona_id, género, rol, nº de bloque de pregunta. El bloque lo asignan las reglas de `decision/roles.py` a partir de los anuncios de la Presidencia («tiene la palabra», «pregunta de la diputada…»); no depende de la IA |
| Fórmula | % de uso = tiempo hablado por la persona en esa pregunta / 150 s |
| Exceso | Una intervención se pasa de tiempo si su uso supera 150 s + 10 s de tolerancia (la Presidencia suele dejar terminar la frase) |
| Salida | % de uso medio por género y rol, y nº y % de intervenciones que se pasan de tiempo, por género |
| Preguntas sin réplica | Si una pregunta tiene menos de 4 intervenciones, quien pregunta no usa la réplica y su uso del tiempo es bajo por el tipo de pregunta, no por falta de protagonismo. Esas preguntas se marcan y no entran en la media de uso del tiempo |
| Interpretación | Se mide, no se penaliza: la herramienta describe. Si la Presidencia corta el micrófono, el audio se detiene y el exceso real puede ser mayor; el Diario lo anota |
| Muestra mínima | 4 voces con género conocido y 300 s, y al menos 2 voces en cada grupo para comparar |
| Validación | Comparar los excesos detectados con la anotación manual de 20 min |
| Test | P1 habla 170 s en su pregunta → uso 113 %, exceso sí. P2 habla 140 s → uso 93 %, exceso no |

### M03a/M03b · Intervenciones y voces por pregunta (control de calidad)

| Campo | Contenido |
|---|---|
| Pregunta | ¿Está separando bien las voces y las preguntas el sistema? |
| Tipo | Determinista. Son dos controles complementarios: M03a y M03b |
| Definición de intervención | Sucesión de fragmentos de la misma voz dentro de un bloque de pregunta. Las pausas no cuentan. Una intervención solo termina cuando habla otra voz (sin contar la Presidencia) durante al menos **5 s seguidos en total**; los tramos más cortos de otra voz (un «gracias», un ruido, un aplauso mal atribuido) no la cortan |
| M03a · Fórmula | Intervenciones por pregunta = nº de intervenciones (sin Presidencia) / nº de bloques de pregunta |
| M03a · Valor esperado y umbral | Unos 4 (pregunta, respuesta, réplica y dúplica). Correcto entre 3 y 6. Si hay referencia oficial, la diferencia debe ser como mucho de ±0,5 |
| M03b · Fórmula | Voces por pregunta = nº de voces (sin Presidencia) que hablan en total al menos 5 s en el bloque |
| M03b · Valor esperado | 2 (quien pregunta y quien responde). Con 3 o más, aviso con la lista de bloques a revisar |
| Lectura conjunta | M03a normal y M03b = 2: correcto. M03a alto: una voz partida en varias. M03b de 3 o más: preguntas mal cortadas o juntadas. Los dos altos: revisar la sesión |
| Referencia oficial | Lista de intervenciones del archivo audiovisual (sin Presidencia de la Cámara): 2026 = 66 intervenciones (16 preguntas con 4 y 1 con 2); 2022 = 73 (17 con 4, 1 con 2 y 1 con 3); 2018 = 76 (18 con 4 y 2 con 2). Es decir, 3,9 / 3,8 / 3,8 por pregunta |
| Por qué no se usa la pausa | La definición anterior (pausa de menos de 1 s) partía las intervenciones con cada aplauso o rumor: daba 6,7 / 8,9 / 7,1 frente a 3,9 / 3,8 / 3,8 oficiales. Medía aplausos, no la separación de voces, y podía sesgar la duración media por género si un grupo recibe más aplausos o rumores |
| Por qué 5 s | Equilibra los dos controles. Con menos, M03b da falsas alarmas por interrupciones breves (con 2 s avisa en V007, bloque 13, sin que haya ningún problema); con 7 s o más se borran intervenciones reales. Con 5 s se puede perder alguna intervención muy breve (V007: 73 frente a 76 oficiales), dentro del margen de ±0,5. El umbral se aplica al tiempo total seguido de la otra voz, no a los fragmentos de Whisper, así que no depende de cómo corte el texto el modelo. Se confirmará con la sesión de desarrollo (V008) |
| Sensibilidad (V005 / V006 / V007) | Sin umbral: 3,9 / 4,2 / 3,9. 1 s y 2 s: 3,9 / 3,9 / 3,9. 3 s: 3,8 / 3,9 / 3,7. **5 s: 3,8 / 3,9 / 3,7**. 10 s: 3,6 / 3,8 / 3,3. 20 s: 3,4 / 3,6 / 2,8 (ya borra intervenciones reales). Zona estable entre 1 y 5 s (varía menos de 0,2). M03b con 5 s: solo avisa en V006, bloque 13 (dos preguntas juntas: límite de Whisper, ver #124) |
| Validación | Con 5 s: 3,82 / 3,89 / 3,65 frente a 3,88 / 3,84 / 3,80 oficiales (diferencia −0,06 / +0,05 / −0,15). En V006 el sistema detecta 18 bloques de 19: la pregunta 13 no tiene anuncio en la transcripción (#124). Cifras del 26/10/2026, con los ficheros regenerados |
| Plan B | Si no da tiempo a implementarlo antes del cierre: intervención = cambio de voz, sin umbral (3,9 / 4,2 / 3,9; diferencia de +0,4 como mucho) |
| Dato adicional | Duración media de la intervención por género (descriptivo), calculada con esta definición |
| Test | Bloque con A 60 s, pausa de 3 s, A 40 s, B 2 s (ruido), A 20 s, B 90 s, A 30 s, B 25 s → M03a = 4 intervenciones (A, B, A, B); M03b = 2 voces |

### M04 · Brecha y ratio de paridad

| Campo | Contenido |
|---|---|
| Pregunta | ¿Las mujeres intervienen en proporción a su presencia? |
| Tipo | Determinista |
| Fórmulas | **a) Brecha de tiempo** = % tiempo de mujeres (M02) − % de mujeres entre quienes intervienen (M01), en puntos. **b) Ratio** = tiempo medio por mujer / tiempo medio por hombre (1 = equidad). **c) Brecha de preguntas** = % de preguntas formuladas por mujeres − % de diputadas con escaño ese día (medida A, apartado 4 bis), en puntos |
| Dato externo | % de diputadas con escaño. Se calcula de dos maneras: **medida A** (el día de la sesión, la que se usa) y **medida B** (toda la legislatura, para medir el error). Ver apartado 4 bis |
| Error | Se calcula la brecha c) con A y con B y se comprueba si la conclusión cambia (apartado 4 bis) |
| Lectura | Brecha negativa o ratio < 1: las mujeres intervienen menos de lo que les correspondería |
| Umbral | \|brecha\| ≥ 15 puntos (15,0 incluido), con la regla de conclusiones del apartado 3 |
| Muestra mínima | 2 personas por grupo y al menos 10 preguntas válidas |
| Test | Mujeres 40 % de las personas y 30 % del tiempo → brecha −10 puntos |

### M06 · Preguntas a quien encabeza el Gobierno en la sesión

| Campo | Contenido |
|---|---|
| Pregunta | ¿Quién ocupa los turnos más visibles de la sesión? |
| Tipo | Determinista. Las preguntas a quien encabeza el Gobierno salen del anuncio de la Presidencia («preguntas dirigidas al señor presidente del Gobierno»); el cargo que cita Qwen en M09 sirve para comprobarlo |
| Definición | Preguntas dirigidas a **quien encabeza el Gobierno en la sesión**: la Presidencia del Gobierno o, si no comparece, la Vicepresidencia Primera (se sigue el orden de rango del Gobierno). Se indica siempre a qué cargo corresponde en cada sesión |
| Fórmula | Nº y % de esas preguntas formuladas por mujeres |
| Por qué sustituye a «apertura y cierre» | En la sesión de control siempre abre la Presidencia de la Cámara. El turno de mayor visibilidad es la pregunta a quien encabeza el Gobierno, que suelen hacer las personas que lideran los grupos |
| Por qué la regla de sustitución | En la sesión de 2026 la Presidencia del Gobierno no recibe preguntas y las primeras van a la Vicepresidencia Primera. Sin la regla, 2026 quedaría sin dato y la comparación entre años no sería posible |
| Datos de referencia (lista oficial de intervenciones) | 2018: 3 preguntas a la Presidencia del Gobierno, 0 de mujeres. 2022: 3 a la Presidencia del Gobierno, 2 de mujeres. 2026: 5 a la Vicepresidencia Primera, 2 de mujeres |
| Muestra mínima | Entre 3 y 5 por sesión: solo descriptiva por sesión; la comparación se hace con las 3 sesiones juntas |
| Validación | Orden del día y lista de intervenciones del archivo audiovisual. VIS Open coincide en las tres sesiones (26/10/2026): 2018, 0 % de 3; 2022, 67 % de 3; 2026, 40 % de 5 |

### M09 · Preguntas recibidas (con IA)

| Campo | Contenido |
|---|---|
| Pregunta | ¿A quién se dirigen las preguntas: a ministras o a ministros? |
| Tipo | IA (clasificación) + determinista (conteo) |
| Definición | Una pregunta recibida es una intervención con rol PREGUNTA que formula una pregunta a un miembro del Gobierno. **La destinataria es quien responde a continuación, y la decide el código por el orden de las voces**, no la IA |
| Papel de la IA | Qwen recibe cada bloque, también lo que lee la Presidencia, y devuelve un JSON con `is_question` (sí/no), `confidence` (0 a 1), `evidence` (la cita literal en la que se basa) y el cargo al que se dirige la pregunta. **En la sesión de control, si la Presidencia anuncia la pregunta, cuenta como pregunta aunque el modelo diga que no**: está en el orden del día y se formula en su turno, aunque se argumente sin una frase interrogativa. En otros formatos decide el modelo (`confidence` de 0,7 o más). Lo que dice el modelo en cada bloque se guarda siempre (`modelo_por_pregunta` en `m09.json`) para evaluarlo frente a la lista oficial. El cargo sirve para separar las preguntas a quien encabeza el Gobierno (M09 c y M06) y **avisar si no coincide** con quien responde según el orden de las voces. La IA no calcula ninguna cifra. Implementado en las PR #104 y #153 |
| Fórmulas | **a)** Nº de preguntas recibidas por persona y por género. **b) Normalizada** = preguntas recibidas por ministras / nº de ministras que responden, frente a lo mismo para ministros. Equivale a comparar el % de preguntas recibidas con el % de ministras. Sin normalizar, solo reflejaría la composición del Gobierno. **c) Quien encabeza el Gobierno, aparte:** las preguntas a la Presidencia del Gobierno (o a la Vicepresidencia Primera si la Presidencia no comparece, igual que en M06) se cuentan por separado y no entran en b), porque recibe varias preguntas fijas por su cargo y desequilibraría la comparación |
| Referencia | La igualdad (mismas preguntas por ministra que por ministro) es el punto de referencia, no lo esperado. Una diferencia es una señal para investigar, no una prueba de trato desigual |
| Tabla descriptiva | Nº de preguntas recibidas por cada ministerio y género de quien lo ocupa, por sesión. Sale del orden del día. Permite ver si las preguntas se concentran en pocos ministerios |
| Limitación: variable de confusión | Las preguntas dependen también de la actualidad de cada ministerio: un ministerio con un tema candente recibe más preguntas por el tema, no por el género de quien lo dirige. Con 17 a 20 preguntas por sesión no se puede separar ese efecto (quedarían 1 o 2 preguntas por ministerio). Se declara en el informe y en la presentación y no se sacan conclusiones de género a partir de M09 b) sin tenerlo en cuenta |
| Casos límite | Pregunta «al Gobierno» sin cargo: cuenta para quien responde. Pregunta respondida por otro ministerio: cuenta para quien responde y se anota |
| Revisión humana | `confidence` < 0,7 → pasa a revisión. También pasa a revisión cualquier pregunta en la que el cargo citado por Qwen no coincida con quien responde. La cita `evidence` permite comprobar cada decisión sin volver a escuchar el audio |
| Validación | Del recuento: M09 coincide con la lista oficial en 2018 (0,81) y 2026 (0,75); en 2022 da 0,86 frente a 0,73 porque falta la pregunta 13 (#124). Del modelo (Qwen3.5-9B, 27/10/2026, `modelo_por_pregunta` frente a la lista oficial): marca como pregunta 52 de 55 (95 %); acierta si va a una ministra o a un ministro en 46 de 47 que dan pista (5 sin pista); nombra a quien encabeza el Gobierno en 5 de 11, sin falsos positivos, porque suele devolver cómo se llama a la persona en la sala («señora ministra», «señor presidente»). Por eso, en la sesión de control, el recuento lo decide el anuncio de la Presidencia (#55) |
| Test | 3 turnos PREGUNTA dirigidos a «la señora ministra» (2) y «el señor ministro» (1), con 1 ministra y 1 ministro → normalizada: 2,0 frente a 1,0 |

### M13 · Calidad del dato

| Campo | Contenido |
|---|---|
| Pregunta | ¿Cuánto tiempo no sabemos atribuir? |
| Tipo | Determinista |
| Fórmula | % = (tiempo `desconocido` + tiempo `sin_atribuir`) / tiempo total de voz del tramo (sin Presidencia, si está identificada). Se informan también por separado |
| Umbral | Más del 20 % (20,0 todavía es válido): la sesión es «no concluyente». Además debe ser menor que la brecha de M04 |
| Lectura | Se muestra siempre, junto a cada resultado |
| Ejemplo real | En la prueba V004, un 30 % del tiempo quedó como desconocido; la voz más larga (probablemente la Presidencia) no tenía ninguna pista |

## 4 bis. Dato de referencia: composición de la cámara (medidas A y B)

M04 c) necesita saber qué % de las personas que podían preguntar eran mujeres. Se calcula de dos maneras y se mide el error entre ambas.

### Las dos medidas

| | Medida A · Composición del día | Medida B · Composición de la legislatura |
|---|---|---|
| Qué cuenta | Quién tenía escaño el día de la sesión | Todas las personas que ocuparon escaño en algún momento de la legislatura |
| Regla | `FECHACONDICIONPLENA` ≤ fecha de la sesión **y** (`FECHABAJA` vacía **o** `FECHABAJA` > fecha de la sesión). Se usa la condición plena porque solo desde ese día la persona puede ejercer, incluido preguntar; si estuviera vacía, `FECHAALTA`. Se cuentan **personas únicas** (quien cambia de grupo aparece dos veces en el CSV) | Todas las personas de la legislatura, sin filtrar por fecha |
| Fórmula | % mujeres A = mujeres con escaño ese día / total con escaño ese día | % mujeres B = mujeres de la legislatura / total de la legislatura |
| Control de calidad | **350**: válido. **Entre 340 y 349**: válido con aviso («N escaños ocupados: hay vacantes ese día»); el denominador es N, porque un escaño vacío no es una persona que pueda preguntar. **Menos de 340 o más de 350**: error, no se calcula M04 c) hasta revisar los datos | Debe coincidir con el buscador oficial (consultado el 22/10/2026): XV 412, XIV 407, XII 393 |
| Valores conocidos | XV (30/09/2026): 157/350 = **44,9 %** · XIV (05/10/2022): 149/349 = **42,7 %**, con **349** escaños ocupados por una vacante real (S/C de Tenerife, sin sustituto desde el 22/10/2021) · XII (19/09/2018): 145/350 = **41,4 %** | XV 189/412 = **45,9 %** · XIV 174/407 = **42,8 %** · XII 161/393 = **41,0 %** |
| Ventaja | Exacta | Sencilla; no necesita fechas |
| Inconveniente | Necesita las fechas de alta y baja | Incluye a personas que no tenían escaño ese día; se desvía más cuantas más sustituciones haya |

Las dos miden **quién tenía escaño**, no quién estaba presente en la sala: para M04 cuenta quién podía preguntar.

### Medición del error

El error se mide en dos niveles:

1. **En el dato de referencia:** diferencia = % B − % A, en puntos, para cada sesión.
2. **En el resultado final (el que importa):** se calcula la brecha de preguntas de M04 c) con A y con B, y se comprueba si la conclusión cambia según la regla del apartado 3.

| Resultado | Lectura |
|---|---|
| La conclusión es la misma con A y con B | La aproximación B habría sido suficiente: no era imprescindible el dato de cada día. Se usa A igualmente porque está automatizada |
| La conclusión cambia | La aproximación B no sirve: el dato del día era necesario |

Salida para la presentación, una fila por sesión: % A, % B, diferencia en puntos, brecha M04 c) con A, brecha con B y si cambia la conclusión (sí/no).

### Fuente

Datos abiertos del Congreso, «Diputados y Diputadas»: https://www.congreso.es/es/opendata/diputados. Reutilización permitida citando la fuente y sin alterar el contenido (aviso legal de congreso.es).

### Requisitos para la implementación (para quien programe)

Descarga de los datos

1. Los CSV se obtienen de https://www.congreso.es/es/opendata/diputados.
2. Los nombres de los ficheros llevan una marca de tiempo que cambia (por ejemplo `odsDiputados14__20261021050323.csv`), así que no se escriben fijos: se localizan en esa página buscando el patrón del nombre.
3. Ficheros por legislatura: `odsDiputadosNN` (NN = número de legislatura con dos cifras). Para la legislatura en curso no existe ese fichero: se usan `DiputadosActivos` + `DiputadosDeBaja`.
4. Se guardan en `data/externos/congreso/`, fuera del repositorio, igual que los vídeos.
5. Cada descarga se registra con fecha y huella SHA-256, como en el manifiesto, para saber con qué versión de los datos se calculó cada cifra.
6. Si el fichero ya está descargado, no se vuelve a descargar.
7. La web del Congreso bloquea las descargas desde servidores como OVH («Access Denied»), así que el camino habitual es **descargar los CSV a mano** desde el navegador y dejarlos en `data/externos/congreso/`. El programa lee los ficheros de esa carpeta y, si no están, avisa sin fallar en silencio.

Cálculo

8. La legislatura y la fecha se toman del manifiesto (`fecha_evento`) de cada vídeo.
9. Medida A: se aplica la regla de condición plena y baja, contando personas únicas. Medida B: todas las personas de la legislatura.
10. Los CSV por legislatura no tienen columna de sexo (columnas: NOMBRE, CIRCUNSCRIPCION, FORMACIONELECTORAL, FECHACONDICIONPLENA, FECHAALTA, FECHABAJA, GRUPOPARLAMENTARIO, fechas de grupo y BIOGRAFIA). El sexo se obtiene por un método documentado, por ejemplo cruzando con el fichero «Diputadas» de los datos abiertos. Si no se puede determinar, «desconocido», que se informa aparte.
11. Controles: A según la tabla de control (350 válido; 340 a 349 válido con aviso; fuera de ese rango, error). B debe coincidir con el buscador oficial. Mientras no esté calculada la medida A, la B se puede usar para pruebas; los resultados usan siempre la A.
12. Se calcula la brecha de M04 c) con A y con B y se aplica la regla de conclusiones a las dos.

Salida

13. Por sesión: total, mujeres, hombres y desconocido de A y de B; % A; % B; diferencia en puntos; brecha M04 c) con A y con B; si cambia la conclusión; resultado de los controles.
14. Esta salida alimenta M04 c) (que usa A) y la tabla de error de la presentación.

Pruebas

15. Test de juguete (ejemplo inventado con resultado conocido, para comprobar que el cálculo es correcto). Un Congreso de 3 personas, donde la Persona 3 sustituye a la Persona 2:

    | Persona | Sexo | Alta | Baja |
    |---|---|---|---|
    | Persona 1 | mujer | 2023-08-17 | sin baja |
    | Persona 2 | hombre | 2023-08-17 | 2025-01-10 |
    | Persona 3 | hombre | 2025-01-10 | sin baja |

    Fecha de la sesión: 2026-09-30. Resultado esperado:
    - Medida A (ese día): Persona 1 y Persona 3 → 1 mujer y 1 hombre → **50 %**. La Persona 2 queda fuera porque salió antes de la sesión.
    - Medida B (toda la legislatura): las 3 personas → 1 mujer y 2 hombres → **33,3 %**.
    - Diferencia: **16,7 puntos**.
16. Con datos reales: A da 350 en 2026-09-30 y 2018-09-19, y 349 con aviso en 2022-10-05; B coincide con 412, 407 y 393.
17. Control de A: 350 → válido sin aviso; 349 y 345 → válido con aviso y ese denominador; 339 y 351 → error; una persona con dos filas (cambio de grupo) cuenta una sola vez.

Columnas confirmadas con el CSV de la XIV (ver punto 10).

## 4 ter. Parámetros para el marco de métricas (`metrics/`)

Valores que pide `docs/METRICAS_MARCO.md` para cada métrica. Sustituyen a los provisionales (2 voces y 60 s con género conocido).

| Métrica | `min_speakers_known_gender` | `min_known_gender_seconds` | Umbral (`gap_is_conclusive`) | Margen | Notas para el código |
|---|---|---|---|---|---|
| M01 | 1 | 0 | No aplica (descriptiva) | No aplica | Recuento por género y rol |
| M02 | 4 | 300 | No aplica (descriptiva) | % desconocido + sin atribuir | Además, 2 voces por grupo para comparar |
| M02b | 4 | 300 | No aplica (descriptiva) | % desconocido + sin atribuir | Usa el nº de bloque de pregunta de `decision/roles.py` (reglas, sin IA) |
| M03a | 2 | 60 | Rango correcto: 3 a 6 intervenciones por pregunta; con referencia oficial, diferencia de ±0,5 como mucho | No aplica | Control de calidad. Une los fragmentos de la misma voz sin mirar la pausa; los tramos de otra voz de menos de 5 s en total no cortan la intervención. Usa los bloques de `decision/roles.py` |
| M03b | 2 | 60 | Valor esperado: 2 voces por pregunta; aviso con 3 o más | No aplica | Control de calidad. Cuenta las voces (sin Presidencia) que hablan en total al menos 5 s en el bloque y lista los bloques con 3 o más |
| M04 | 4 | 600 | **15 puntos** | % desconocido + sin atribuir | Además, 2 voces por grupo y 10 preguntas válidas. La brecha c) necesita un dato externo que no está en la línea de tiempo: el % de diputadas (apartado 4 bis), que se pasa como entrada |
| M06 | 1 | 0 | No aplica (descriptiva por sesión) | No aplica | Aplica la regla de sustitución (Vicepresidencia Primera si no comparece la Presidencia del Gobierno) e indica el cargo usado. La comparación se hace sumando las 3 sesiones |
| M09 | 4 | 600 | No aplica en b) por la variable de confusión (solo descriptiva) | No aplica | En la sesión de control, la pregunta anunciada por la Presidencia cuenta siempre; en otros formatos, la salida de Qwen con `confidence` de 0,7 o más (si no, revisión humana). Lo que dice el modelo se guarda siempre para evaluarlo |
| M13 | 0 | 0 | Mayor del 20 % → sesión «no concluyente» | No aplica | Se calcula siempre, aunque no haya muestra |

Por qué estos valores: 4 voces con género conocido es el mínimo para tener 2 por grupo; 300 s (5 min) equivale a una pregunta completa; 600 s (10 min) son unas dos preguntas, mínimo razonable para comparar grupos. Son valores iniciales: se revisan con los datos reales y la anotación manual.

Limitación del marco que afecta a estas métricas: el código suma la duración de los eventos y no resta los solapes entre voces. En la sesión de control los solapes son pocos, así que el efecto es pequeño; se comprueba con la anotación manual.

## 5. Descartadas para el Congreso

| Métrica | Motivo |
|---|---|
| M05 Turno más largo | El tiempo está limitado por reglamento |
| M06 original (apertura y cierre) | Siempre abre la Presidencia; sustituida por la nueva M06 |
| M08 Palabra cedida por la moderación | El orden lo fija el orden del día, no la Presidencia |
| M10 Distribución por cuartiles | El orden de las preguntas está fijado |
| M11 Rol en el debate | En el Congreso el rol lo fija el formato (preside, pregunta o responde) y lo asignan las reglas de `decision/roles.py` a partir de los anuncios de la Presidencia (apartado 2, regla «Roles»). No hace falta IA |
| M14 Manos levantadas, M15 y M16 | En el pleno no se pide la palabra levantando la mano y las votaciones son electrónicas. Descarte acordado por el equipo (22/10/2026) |
| M17 Equidad | Incluida en M04 (ratio) |
| Conteo de escaños ocupados desde el vídeo | Saber si cada asiento lo ocupa una mujer o un hombre mirando la imagen es inferir el género por la apariencia, que el proyecto prohíbe (RNF-05 y RNF-13). Además, la cámara enfoca a quien habla y no muestra los 350 escaños. Y no hace falta: M04 mide quién podía preguntar, no quién estaba sentada |

## 6. Evolución futura

| Métrica | Idea |
|---|---|
| M07 Interrupciones y llamadas al orden | El Diario anota rumores, protestas y llamadas al silencio de la Presidencia. ¿Durante las intervenciones de quién ocurren más? |
| M12 Temas por género | ¿Sobre qué se pregunta a mujeres y a hombres? El orden del día ya incluye el asunto |
| M18 Cortes de la Presidencia | ¿A quién se le retira la palabra por agotar el tiempo? |
| Explicar cada vacante | Que el sistema indique automáticamente qué escaños están vacíos el día de la sesión (por circunscripción) y desde cuándo, en lugar de solo avisar del total |
| Presencia real en la sala | Si interesara saber quién estaba presente, las votaciones nominales de los datos abiertos del Congreso registran quién votó ese día. Cruzándolas con la lista de diputadas se obtiene el sexo sin usar imágenes |
| M09 controlando el tema | Comparar el mismo ministerio cuando lo ocupa una mujer y cuando lo ocupa un hombre: el tema es el mismo y solo cambia el género. Las sesiones elegidas ya tienen un caso: Ministra de Hacienda en 2022 y Ministro de Hacienda en 2026. Con más sesiones se puede hacer de forma sistemática |
| Más sesiones y formatos | Debates de leyes, comisiones, Senado |

## 7. Pendiente

- [x] % de diputadas de la legislatura completa (XV, XIV, XII) para la sensibilidad de M04.
- [x] Descargar los CSV de datos abiertos, confirmar las columnas y programar las medidas A y B (controles: 350 y buscador oficial).
- [x] Tabla de error: medida A frente a B y su efecto en la conclusión de M04 (#55, 26/10/2026: la conclusión no cambia en ninguna sesión).
- [x] Acordado con el equipo (22/10/2026): descartar M14, sustituir M06 y añadir M02b.
- [x] M06: regla de sustitución por la Vicepresidencia Primera cuando no comparece la Presidencia del Gobierno (decisión de Ivette, 22/10/2026).
- [x] Comprobar el reparto de unos 150 s por persona con el tiempo real de la primera pregunta de cada sesión (#55).
- [x] Ajustar `metrics/congreso.py` a estas definiciones y a los parámetros del apartado 4 ter (Veru), siguiendo los pasos de `docs/METRICAS_MARCO.md`: M03a y M03b en el panel (#143, PR #160).
- [x] Programar M09 con Qwen según esta definición (Sabrina, PR #104 y #153).
- [x] Medir el modelo (detección de preguntas y cargo) con `modelo_por_pregunta` (#55, 27/10/2026; ver M09, «Validación»).
