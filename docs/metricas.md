# Métricas · Equipo 6, VIS Open

Definiciones formales de las métricas de esta entrega. Borrador de Ivette para revisar con el equipo.

## 1. Contexto: qué analizamos

- **Unidad de análisis:** el bloque de preguntas de una sesión de control al Gobierno del Congreso de los Diputados (tramo_inicio a tramo_fin del manifiesto).
- **Sesiones:** V005 (XV, 30/09/2026), V006 (XIV, 05/10/2022) y V007 (XII, 19/09/2018).
- **Por qué este formato:** es comparable entre años, tiene referencia oficial (orden del día y Diario de Sesiones) y los turnos están ordenados, lo que facilita separar las voces.
- **Limitación importante:** en la sesión de control el tiempo de cada pregunta está fijado por el Reglamento. Las diferencias de tiempo entre mujeres y hombres vienen sobre todo de **cuántas veces** habla cada grupo, no de cuánto dura cada intervención. Por eso las métricas ponen el foco en el reparto de oportunidades: quién pregunta, a quién se pregunta y quién ocupa los turnos más visibles.

## 2. Reglas comunes a todas las métricas

| Regla | Definición |
|---|---|
| Roles | Cada persona tiene un rol: `PRESIDENCIA` (quien preside), `PREGUNTA` (diputada o diputado que formula) o `GOBIERNO` (quien responde). |
| Presidencia | Se excluye de todas las métricas salvo M13. Se informa aparte. |
| Género | `mujer`, `hombre` o `desconocido`, atribuido por pistas del lenguaje («la señora», «el señor», «la ministra»). Nunca se infiere de la voz ni de la cara. Se informa como género atribuido, no verificado. |
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
| Separar quien pregunta (diputadas y diputados) de quien responde (Gobierno) | Son decisiones distintas, tomadas por personas distintas y en momentos distintos. Quién pregunta lo decide cada grupo parlamentario en cada sesión: mide si los grupos dan la palabra a sus diputadas. Quién responde lo decidió la Presidencia del Gobierno al nombrar ministros: mide la composición del Gobierno. Mezclarlos oculta lo que se quiere medir. Ejemplo (sesión de 2018): preguntan 10 mujeres y 10 hombres (paridad); responden 12 ministras y 7 ministros. Juntos darían un 56 % de mujeres, que reflejaría la composición del Gobierno y no el reparto de la palabra entre diputadas y diputados. Se separa por el rol en cada intervención, no por tener escaño, porque muchos miembros del Gobierno también son diputados |
| Presidencia de la Cámara aparte | Da la palabra en todas las preguntas: su tiempo no refleja protagonismo y distorsionaría todas las métricas |
| Presidencia del Gobierno aparte en M09 b) | Recibe varias preguntas fijas por su cargo |
| Composición de la cámara calculada de dos maneras (A y B) | Para medir el error de usar la aproximación por legislatura y decidir con datos si el dato de cada día es necesario (apartado 4 bis) |
| La IA solo clasifica; las cifras las calcula el código | Transparencia y reproducibilidad: cualquier persona puede repetir el cálculo |
| El género se atribuye por el lenguaje, nunca por la voz o la imagen | Marco ético del proyecto (RNF-05 y RNF-13) y sesgos conocidos de esos sistemas |

## 3. Regla para sacar conclusiones

Una frase del tipo «las mujeres tienen menos protagonismo» solo aparece en el informe si se cumplen las tres condiciones:

1. La brecha de M04 es de **15 puntos o más**.
2. El tiempo sin atribuir (M13) es **menor del 20 %** y **menor que la brecha** (es el margen de error).
3. Se cumple la muestra mínima.

Si falla alguna, el panel muestra «no concluyente» y explica cuál. En el código, esta regla la aplica `gap_is_conclusive` (`metrics/registry.py`), con el umbral de 15 puntos que se fija aquí.

## 4. Métricas de esta entrega

M01, M02 (con la submétrica M02b), M03, M04, M06, M09 y M13.

### M01 · Presencia

| Campo | Contenido |
|---|---|
| Pregunta | ¿Cuántas mujeres y cuántos hombres intervienen, y con qué rol? |
| Tipo | Determinista |
| Entrada | persona_id, género, rol |
| Fórmula | Número de persona_id distintas por género y rol |
| Unidad | Personas y % sobre el total de personas del mismo rol |
| Salida | Tabla rol × género (PREGUNTA y GOBIERNO) |
| Casos límite | Una misma persona separada en dos voces por error cuenta dos veces: se revisa con M03 y con la anotación manual |
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
| Muestra mínima | 2 personas por grupo |
| Validación | Error ≤ 3 puntos en el % de tiempo de mujeres frente a la anotación manual de 20 min |
| Test | P1 mujer 0–10 s, P2 hombre 10–15 s → mujeres 10 s (66,7 %), hombres 5 s (33,3 %) |

#### M02b · Uso del tiempo asignado (submétrica de M02)

| Campo | Contenido |
|---|---|
| Pregunta | ¿Quién agota o sobrepasa el tiempo que le corresponde? Sobrepasarlo es ocupar espacio, una señal de protagonismo |
| Tipo | Determinista |
| Contexto | Cada pregunta dispone de unos 5 minutos: unos 150 s para quien pregunta (pregunta + réplica) y unos 150 s para quien responde (respuesta + dúplica) |
| Entrada | inicio, fin, persona_id, género, rol, nº de pregunta (de M09) |
| Fórmula | % de uso = tiempo hablado por la persona en esa pregunta / 150 s |
| Exceso | Una intervención se pasa de tiempo si su uso supera 150 s + 10 s de tolerancia (la Presidencia suele dejar terminar la frase) |
| Salida | % de uso medio por género y rol, y nº y % de intervenciones que se pasan de tiempo, por género |
| Interpretación | Se mide, no se penaliza: la herramienta describe. Si la Presidencia corta el micrófono, el audio se detiene y el exceso real puede ser mayor; el Diario lo anota |
| Muestra mínima | 2 personas por grupo |
| Validación | Comparar los excesos detectados con la anotación manual de 20 min |
| Test | P1 habla 170 s en su pregunta → uso 113 %, exceso sí. P2 habla 140 s → uso 93 %, exceso no |

### M03 · Turnos por pregunta (control de calidad)

| Campo | Contenido |
|---|---|
| Pregunta | ¿Está separando bien las voces el sistema? |
| Tipo | Determinista |
| Definición de turno | Intervenciones consecutivas de la misma persona separadas por una pausa de menos de 1 s |
| Fórmula | Turnos por pregunta = nº de turnos (sin Presidencia) / nº de preguntas válidas |
| Valor esperado | Unos 4 por pregunta: pregunta, respuesta, réplica y dúplica |
| Umbral | Entre 3 y 6: correcto. Fuera de ese rango: revisar la separación de voces antes de usar el resto de métricas |
| Dato adicional | Duración media del turno por género (descriptivo) |
| Test | 2 preguntas con 4 turnos cada una → 4,0 |

### M04 · Brecha y ratio de paridad

| Campo | Contenido |
|---|---|
| Pregunta | ¿Las mujeres intervienen en proporción a su presencia? |
| Tipo | Determinista |
| Fórmulas | **a) Brecha de tiempo** = % tiempo de mujeres (M02) − % de mujeres entre quienes intervienen (M01), en puntos. **b) Ratio** = tiempo medio por mujer / tiempo medio por hombre (1 = equidad). **c) Brecha de preguntas** = % de preguntas formuladas por mujeres − % de diputadas en la legislatura, en puntos |
| Dato externo | % de diputadas con escaño. Se calcula de dos maneras: **medida A** (el día de la sesión, la que se usa) y **medida B** (toda la legislatura, para medir el error). Ver apartado 4 bis |
| Error | Se calcula la brecha c) con A y con B y se comprueba si la conclusión cambia (apartado 4 bis) |
| Lectura | Brecha negativa o ratio < 1: las mujeres intervienen menos de lo que les correspondería |
| Umbral | 15 puntos, con la regla de conclusiones del apartado 3 |
| Muestra mínima | 2 personas por grupo y al menos 10 preguntas válidas |
| Test | Mujeres 40 % de las personas y 30 % del tiempo → brecha −10 puntos |

### M06 · Preguntas al Presidente del Gobierno

| Campo | Contenido |
|---|---|
| Pregunta | ¿Quién ocupa los turnos más visibles de la sesión? |
| Tipo | Determinista (usa el cargo que cita Qwen en M09 para identificar las preguntas al Presidente del Gobierno) |
| Fórmula | Nº y % de preguntas al Presidente del Gobierno formuladas por mujeres |
| Por qué sustituye a «apertura y cierre» | En la sesión de control siempre abre la Presidencia. El turno de mayor visibilidad es la pregunta al Presidente, que suelen hacer las personas que lideran los grupos |
| Muestra mínima | Hay 2 o 3 por sesión: solo descriptiva por sesión; la comparación se hace con las 3 sesiones juntas |
| Validación | Orden del día |

### M09 · Preguntas recibidas (con IA)

| Campo | Contenido |
|---|---|
| Pregunta | ¿A quién se dirigen las preguntas: a ministras o a ministros? |
| Tipo | IA (clasificación) + determinista (conteo) |
| Definición | Una pregunta recibida es una intervención con rol PREGUNTA que formula una pregunta a un miembro del Gobierno. **La destinataria es quien responde a continuación, y la decide el código por el orden de las voces**, no la IA |
| Papel de la IA | Qwen recibe cada turno y devuelve un JSON con `is_question` (sí/no), `confidence` (0 a 1), `evidence` (la cita literal del turno en la que se basa) y el cargo al que se dirige la pregunta. El cargo sirve para dos cosas: separar las preguntas al Presidente del Gobierno (M09 c y M06) y **avisar si no coincide** con quien responde según el orden de las voces. La IA no calcula ninguna cifra. Implementado en el PR 104 |
| Fórmulas | **a)** Nº de preguntas recibidas por persona y por género. **b) Normalizada** = preguntas recibidas por ministras / nº de ministras que responden, frente a lo mismo para ministros. Equivale a comparar el % de preguntas recibidas con el % de ministras. Sin normalizar, solo reflejaría la composición del Gobierno. **c) Presidencia del Gobierno aparte:** las preguntas a la persona que preside el Gobierno se cuentan por separado y no entran en b), porque recibe varias preguntas fijas por su cargo y desequilibraría la comparación |
| Referencia | La igualdad (mismas preguntas por ministra que por ministro) es el punto de referencia, no lo esperado. Una diferencia es una señal para investigar, no una prueba de trato desigual |
| Tabla descriptiva | Nº de preguntas recibidas por cada ministerio y género de quien lo ocupa, por sesión. Sale del orden del día. Permite ver si las preguntas se concentran en pocos ministerios |
| Limitación: variable de confusión | Las preguntas dependen también de la actualidad de cada ministerio: un ministerio con un tema candente recibe más preguntas por el tema, no por el género de quien lo dirige. Con 17 a 20 preguntas por sesión no se puede separar ese efecto (quedarían 1 o 2 preguntas por ministerio). Se declara en el informe y en la presentación y no se sacan conclusiones de género a partir de M09 b) sin tenerlo en cuenta |
| Casos límite | Pregunta «al Gobierno» sin cargo: cuenta para quien responde. Pregunta respondida por otro ministerio: cuenta para quien responde y se anota |
| Revisión humana | `confidence` < 0,7 → pasa a revisión. También pasa a revisión cualquier pregunta en la que el cargo citado por Qwen no coincida con quien responde. La cita `evidence` permite comprobar cada decisión sin volver a escuchar el audio |
| Validación | Frente al orden del día y la anotación manual: F1 ≥ 0,85 en detectar preguntas y en el destinatario |
| Test | 3 turnos PREGUNTA dirigidos a «la señora ministra» (2) y «el señor ministro» (1), con 1 ministra y 1 ministro → normalizada: 2,0 frente a 1,0 |

### M13 · Calidad del dato

| Campo | Contenido |
|---|---|
| Pregunta | ¿Cuánto tiempo no sabemos atribuir? |
| Tipo | Determinista |
| Fórmula | % = (tiempo `desconocido` + tiempo `sin_atribuir`) / tiempo total de voz del tramo (sin Presidencia, si está identificada). Se informan también por separado |
| Umbral | Mayor del 20 %: la sesión es «no concluyente». Además debe ser menor que la brecha de M04 |
| Lectura | Se muestra siempre, junto a cada resultado |
| Ejemplo real | En la prueba V004, un 30 % del tiempo quedó como desconocido; la voz más larga (probablemente la Presidencia) no tenía ninguna pista |

## 4 bis. Dato de referencia: composición de la cámara (medidas A y B)

M04 c) necesita saber qué % de las personas que podían preguntar eran mujeres. Se calcula de dos maneras y se mide el error entre ambas.

### Las dos medidas

| | Medida A · Composición del día | Medida B · Composición de la legislatura |
|---|---|---|
| Qué cuenta | Quién tenía escaño el día de la sesión | Todas las personas que ocuparon escaño en algún momento de la legislatura |
| Regla | Fecha de alta ≤ fecha de la sesión **y** (fecha de baja vacía **o** fecha de baja > fecha de la sesión) | Todas las personas de la legislatura, sin filtrar por fecha |
| Fórmula | % mujeres A = mujeres con escaño ese día / total con escaño ese día | % mujeres B = mujeres de la legislatura / total de la legislatura |
| Control de calidad | El total debe ser **350**. Si no, se avisa y el dato no se usa hasta revisarlo | Debe coincidir con el buscador oficial (consultado el 22/10/2026): XV 412, XIV 407, XII 393 |
| Valores conocidos | Pendiente de calcular | XV 189/412 = **45,9 %** · XIV 174/407 = **42,8 %** · XII 161/393 = **41,0 %** |
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
7. Si la página cambia y no se encuentran los enlaces, el programa no falla en silencio: avisa y permite usar ficheros descargados a mano en la misma carpeta.

Cálculo

8. La legislatura y la fecha se toman del manifiesto (`fecha_sesion`) de cada vídeo.
9. Medida A: se aplica la regla de alta y baja. Medida B: todas las personas de la legislatura.
10. El sexo se toma de la columna correspondiente del CSV. Si no existe, del tratamiento (Sra./Sr.). Si no se puede determinar, «desconocido», que se informa aparte.
11. Controles: A debe dar 350; B debe coincidir con el buscador oficial. Si alguno falla, se avisa y el dato no se usa hasta revisarlo.
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
16. Con datos reales: A da 350 en las tres sesiones (2026-09-30, 2022-10-05 y 2018-09-19) y B coincide con 412, 407 y 393.

Pendiente: confirmar los nombres de las columnas de alta, baja y sexo en los CSV.

## 4 ter. Parámetros para el marco de métricas (`metrics/`)

Valores que pide `docs/METRICAS_MARCO.md` para cada métrica. Sustituyen a los provisionales (2 voces y 60 s con género conocido).

| Métrica | `min_speakers_known_gender` | `min_known_gender_seconds` | Umbral (`gap_is_conclusive`) | Margen | Notas para el código |
|---|---|---|---|---|---|
| M01 | 1 | 0 | No aplica (descriptiva) | No aplica | Recuento por género y rol |
| M02 | 4 | 300 | No aplica (descriptiva) | % desconocido + sin atribuir | Además, 2 voces por grupo para comparar |
| M02b | 4 | 300 | No aplica (descriptiva) | % desconocido + sin atribuir | Necesita el nº de pregunta de cada turno (de M09) |
| M03 | 2 | 60 | Rango correcto: 3 a 6 turnos por pregunta | No aplica | Control de calidad; necesita el nº de preguntas válidas del orden del día |
| M04 | 4 | 600 | **15 puntos** | % desconocido + sin atribuir | Además, 2 voces por grupo y 10 preguntas válidas. La brecha c) necesita un dato externo que no está en la línea de tiempo: el % de diputadas (apartado 4 bis), que se pasa como entrada |
| M06 | 1 | 0 | No aplica (descriptiva por sesión) | No aplica | La comparación se hace sumando las 3 sesiones |
| M09 | 4 | 600 | No aplica en b) por la variable de confusión (solo descriptiva) | No aplica | Usa la salida de Qwen; confianza < 0,7 → revisión humana |
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
| M14 Manos levantadas, M15 y M16 | En el pleno no se pide la palabra levantando la mano y las votaciones son electrónicas. Descarte acordado por el equipo (22/10/2026) |
| M17 Equidad | Incluida en M04 (ratio) |
| Conteo de escaños ocupados desde el vídeo | Saber si cada asiento lo ocupa una mujer o un hombre mirando la imagen es inferir el género por la apariencia, que el proyecto prohíbe (RNF-05 y RNF-13). Además, la cámara enfoca a quien habla y no muestra los 350 escaños. Y no hace falta: M04 mide quién podía preguntar, no quién estaba sentada |

## 6. Evolución futura

| Métrica | Idea |
|---|---|
| M07 Interrupciones y llamadas al orden | El Diario anota rumores, protestas y llamadas al silencio de la Presidencia. ¿Durante las intervenciones de quién ocurren más? |
| M12 Temas por género | ¿Sobre qué se pregunta a mujeres y a hombres? El orden del día ya incluye el asunto |
| M18 Cortes de la Presidencia | ¿A quién se le retira la palabra por agotar el tiempo? |
| Presencia real en la sala | Si interesara saber quién estaba presente, las votaciones nominales de los datos abiertos del Congreso registran quién votó ese día. Cruzándolas con la lista de diputadas se obtiene el sexo sin usar imágenes |
| M09 controlando el tema | Comparar el mismo ministerio cuando lo ocupa una mujer y cuando lo ocupa un hombre: el tema es el mismo y solo cambia el género. Las sesiones elegidas ya tienen un caso: Ministra de Hacienda en 2022 y Ministro de Hacienda en 2026. Con más sesiones se puede hacer de forma sistemática |
| Más sesiones y formatos | Debates de leyes, comisiones, Senado |

## 7. Pendiente

- [x] % de diputadas de la legislatura completa (XV, XIV, XII) para la sensibilidad de M04.
- [ ] Descargar los CSV de datos abiertos, confirmar las columnas y programar las medidas A y B (controles: 350 y buscador oficial).
- [ ] Tabla de error: medida A frente a B y su efecto en la conclusión de M04, para la presentación.
- [x] Acordado con el equipo (22/10/2026): descartar M14, sustituir M06 y añadir M02b.
- [ ] Ajustar `metrics/borrador.py` a estas definiciones y a los parámetros del apartado 4 ter (Veru), siguiendo los pasos de `docs/METRICAS_MARCO.md`.
- [ ] Programar M09 con Qwen según esta definición (Sabrina).
