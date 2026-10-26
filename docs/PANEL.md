# Panel, informe y evolución

Qué hay que construir en la etapa 7 del plan (responsable: Veru). Es **una sola interfaz**: una aplicación web local hecha con Streamlit, que se abre en el navegador y no necesita servidor ni base de datos.

```bash
streamlit run dashboard/app.py
```

## Asistente de voz y accesibilidad

La ventana del asistente, el modo manos libres y la validación por voz están descritos en [`ACCESIBILIDAD.md`](ACCESIBILIDAD.md); lo que cumple y lo que no, en [`DECLARACION_ACCESIBILIDAD.md`](DECLARACION_ACCESIBILIDAD.md).

## De dónde salen los datos

El panel no calcula nada con IA. Solo lee los ficheros que deja el análisis de cada sesión en `data/processed/<sesión>/`:

- `source.json`: ficha de la sesión (fecha, legislatura, enlace, fuente y huella digital).
- `timeline.json`: línea de tiempo (quién habla, desde qué segundo hasta cuál, y su género con la evidencia).
- `m09.json`: M09 y M06 calculadas con IA sobre los bloques de pregunta (si existe; lo genera `python -m metrics.m09`).
- `resumen.json` y los resultados de las métricas de `metrics/`.
- `video.json`: análisis de vídeo (personas visibles y tiempo en pantalla), si existe.
- `tiempos.json` y `coste.json`: tiempo y coste real de cada paso (los deja `pipeline.sesion`).
- `data/externos/congreso/`: datos abiertos de composición de la cámara (M04 c). Se descargan
  con `python -m sources.diputados` y no se versionan; si faltan, el panel lo dice y M04 c) se
  queda sin dato (la brecha de tiempo a) y el ratio b) se siguen calculando).

Hasta que existan datos reales, se trabaja con los datos sintéticos de `evaluation/synthetic/muestras/` (`make synthetic`).

## Composición de la cámara (M04 c)

M04 c) compara el % de preguntas formuladas por mujeres con el % de diputadas. Ese dato no está
en la línea de tiempo: sale de los datos abiertos del Congreso y se calcula de dos maneras (apartado
4 bis de la definición de métricas de Ivette):

- **A, el día de la sesión:** quien tenía escaño ese día (`FECHAALTA <= fecha < FECHABAJA`). Debe
  sumar 350; de 340 a 349 se usa con aviso (vacantes ese día; el denominador es N); con otro
  número, se avisa y no se usa hasta revisarlo.
- **B, la legislatura completa:** todas las personas que ocuparon escaño. Debe coincidir con el
  buscador oficial (XV 412, XIV 407, XII 393).

El sexo se cruza con las listas oficiales de diputadas y diputados, porque los CSV no traen
columna de sexo; quien no aparece en ninguna lista queda como desconocido, informado aparte.

Los CSV se descargan con `python -m sources.diputados` (quedan en `data/externos/congreso/`, con
fecha y sha256 de cada fichero y sin volver a bajarlos si ya están). La tabla de error para la
presentación se imprime con `python -m metrics.diputadas`: % A, % B, diferencia en puntos, brecha
c) con A y con B, si cambia la conclusión y los avisos.

Estado: XV y XII dan A = 350; **XIV da 349** (sesión del 05/10/2022: una vacante), que se usa con
el aviso «349 escaños ocupados: hay vacantes ese día».

## Pantalla 1 · Panel de una sesión

1. **Selector de sesión** (lista de las sesiones procesadas). Las que no son sesiones de control
   (`tipo_sesion` del manifiesto: pleno, comisión o sin tipo, como la Diputación Permanente o un
   acto) van al final, con su tipo, y sus métricas de preguntas salen «no aplica».
2. **Ficha de la sesión**: fecha, legislatura, tipo de sesión, enlace a la fuente y aviso «Fuente: Congreso de los Diputados, vídeo sin alterar».
3. **Cifras principales**, una tarjeta por métrica, separando siempre mujer / hombre / desconocido:
   - M01 Presencia: personas que intervienen, por género y rol.
   - M02 Tiempo de palabra: minutos y porcentaje por género.
   - M02b Uso del tiempo: porcentaje del tiempo asignado en cada pregunta y excesos.
   - M03a Intervenciones por pregunta y M03b Voces por pregunta (control de calidad). M03a
     espera de 3 a 6 intervenciones; M03b espera 2 voces y avisa con 3 o más. La definición
     está en `docs/metricas.md`.
   - M04 Brecha de paridad: % del tiempo de las mujeres menos su % entre quienes intervienen;
     debajo, el % de diputadas ese día (A) y en la legislatura (B) para la brecha de preguntas.
     Con 340–349 escaños se usa con aviso; con otro número, no se usa hasta revisarla.
   - M06 Preguntas al Presidente del Gobierno (o a la Vicepresidencia Primera si no comparece):
     % formuladas por mujeres.
   - M09 Preguntas recibidas: por ministra y por ministro. En la sesión de control cuenta toda
     pregunta que anuncia la Presidencia; el modelo da el cargo y la cita, nunca las cifras.
   - M13 Sin atribuir: porcentaje de tiempo en que no se sabe quién habla.
   Si una métrica no tiene muestra suficiente, la tarjeta dice «no concluyente» en lugar de la
   cifra; si no se aplica a la sesión (por ejemplo, no hay bloques de pregunta), dice «no aplica».
   Debajo, una tabla con las métricas del marco aún pendientes (M07, M12, M18) y M17 (incluida en
   M04). Las descartadas para el Congreso (M05, M08, M10, M14–M16) no se muestran.
4. **Gráfico de barras** del tiempo de palabra por género.
5. **Línea de tiempo** de la sesión: una franja horizontal coloreada según el género de quien habla en cada momento; en gris, la parte del vídeo que no se analiza.
6. **Tabla de intervenciones**: código anónimo de la persona (Persona 1, Persona 2…), minuto de inicio, duración, género y la evidencia del género (la frase y el minuto, con el nombre sustituido por el código, por ejemplo «tiene la palabra la señora [Persona 3]»). Las voces sin pista aparecen como `desconocido`. Nunca se muestran nombres.
7. **Aviso de método**, siempre visible: «El género asignado por IA solo se hace por pistas del lenguaje de la sesión, nunca por la cara ni la voz. Los resultados son orientativos y requieren revisión humana.»

## Subtítulos para personas sordas

El vídeo de la sesión y los cortes de «Human in the loop» llevan una pista de subtítulos (WebVTT, «Español (automático)») que sale de la transcripción: líneas de hasta 42 caracteres, dos por subtítulo, con «Persona N:» al cambiar de voz. Se activan y desactivan con el botón «CC» del reproductor, y se pueden descargar (`.vtt`). Límites: son automáticos (Whisper) y pueden tener errores (WER aún sin medir); los nombres propios salen como «Persona N» por la seudonimización; solo cubren el español transcrito. Para cumplir de verdad con accesibilidad en una publicación final, habría que revisarlos a mano.

## Escala tipográfica

De mayor a menor: **héroe** (título de la sesión, hasta 70 px), **título 1** (secciones, 50 px), **título 2** (subsecciones, 35 px), **texto 1** (párrafos y formularios, 27 px), **texto 2** (pies, tablas, transcripción, 22 px) y el **mínimo** (20 px: barra lateral, etiquetas, chips y letra de los gráficos). Nada baja del tamaño de la barra lateral. Los tamaños se definen una sola vez, como variables `--fs-*` al principio de `dashboard/style.css` (en pantalla estrecha se reducen solos, sin bajar del mínimo legible).

## Diseño del panel

Estilo editorial y sobrio, pensado para proyectar: fondo de papel cálido, tinta oscura, un solo acento (verde azulado) y títulos con tipografía con serifa. Los colores de género (ciruela y verde azulado) se reservan para los gráficos. Cada parte de la sesión (vídeo, Human in the loop, métricas, audio, análisis de vídeo, descargas) es una tarjeta, con una barra de navegación fija arriba, desplazamiento suave, aparición progresiva y efectos al pasar el ratón (se desactivan si el sistema pide menos movimiento). Todo vive en `dashboard/style.css` y en `.streamlit/config.toml` (tema), sin fuentes ni recursos externos. En móvil la navegación se desliza en una sola línea.

## Human in the loop: confirmar el género de las voces

Término a usar tal cual en la presentación y el vídeo. En la pantalla de sesión, el vídeo (si el original está en `data/raw/`, solo en el equipo local) va a la izquierda y la pantalla es una sola columna, de arriba abajo: (1) el vídeo completo; (2) «Human in the loop»: los tramos de cada voz `desconocido`, con su clip y el formulario para confirmar; (3) el análisis de la sesión: métricas, tiempo de palabra, línea de tiempo, análisis de vídeo (personas visibles y tiempo en pantalla), transcripción (cada trozo tiene un ▶ que mueve el vídeo de arriba a ese minuto) e intervenciones. Para cada voz que el lenguaje dejó en `desconocido` se ven sus tramos («Persona 1: de 0:00 a 0:20») con el vídeo en ese punto. Cada anotadora decide mujer, hombre o desconocido y su seguridad; se guarda en `review_anotadora_1.csv` y `review_anotadora_2.csv`. El género solo pasa a las cifras cuando **las dos coinciden** (procedencia `anotacion_percibida`); si no, sigue `desconocido`. El sistema nunca lo decide por la cara ni por la voz: lo decide una persona.

## Acceso: usuario, contraseña y segundo factor

Si existe `data/usuarios.json`, el panel pide ID de usuario, contraseña y el código de 6 cifras de una app de autenticación (TOTP, RFC 6238), y no carga datos hasta entrar. Sin ese fichero va en modo abierto (demo sintética o uso local): cada revisión se guarda como `anotadora_1` o `anotadora_2`, según la que elijas, y hacen falta las dos para confirmar.

- Alta (cada persona, en su equipo): `python -m dashboard.auth add <id>`. La contraseña se escribe sin mostrarse (mínimo 12 caracteres) y se enseña una sola vez el URI del autenticador. El ID es un código (`ana-1`), nunca un nombre ni un correo. También `list` y `remove <id>`.
- El ID de conexión queda en `annotator_id` de cada revisión. Dos revisiones del mismo ID no cuentan como confirmación: hacen falta dos personas distintas.
- Contraseñas con scrypt y sal; nunca en claro. Cinco fallos en 15 minutos bloquean 15 minutos. Todo intento se anota en `data/auth_log.jsonl` (sin contraseñas ni códigos).
- `data/` no se sube al repo. Límite conocido: sin caducidad de sesión ni TLS propio; para compartirlo en una red, detrás de un proxy HTTPS.

## Human in the loop: cortes uno a continuación de otro

La Presidencia no sale para validar: va fuera de M02 y M04 (`docs/metricas.md`, §2). Cada voz que quedó en `desconocido` se valida con **cortes de 9 s**, puestos uno detrás de otro por orden en el vídeo (no agrupados por voz). Cada corte trae su clip, lo que se dice en él y su formulario. Validar una voz en un corte **vale para todos los cortes de esa voz**: los demás pasan a «ya validada por ti como…» y no hace falta repetirlo. Cada anotadora lo hace por su cuenta, y el género solo entra en las cifras cuando las dos coinciden. El género y la seguridad empiezan sin marcar: «Guardar» sin elegir no registra nada.

## Informe descargable (PDF)

El botón **«Descargar informe (PDF)»** de la pantalla de sesión genera un PDF (ReportLab, BSD) con:

- La ficha de la sesión y la fuente, y un resumen con la diferencia de tiempo mujeres − hombres (2 × M02 − 100, sobre el tiempo con género conocido) y qué pasaría según cómo fueran las voces sin género.
- Las métricas con su valor o «no concluyente», y por qué.
- Análisis de audio: tiempo de palabra por género, línea de tiempo y voces.
- Análisis de vídeo (MediaPipe, sin caras): personas visibles a lo largo del vídeo, tiempo en pantalla y pistas.
- El método y los límites.

La transcripción completa no va en el PDF: se descarga aparte en un CSV («Descargar transcripción (CSV)»), y el PDF enlaza a él. `python -m dashboard.export` guarda ambos ficheros de todas las sesiones en `data/informes/` (con `--link-base URL` el enlace apunta a un almacenamiento privado donde se suba el CSV).

## Pantalla 2 · Evolución entre sesiones

Compara las sesiones analizadas, ordenadas por fecha. Filtros por año, mes y tipo de sesión; por
defecto, solo las sesiones de control (V005–V007, las de evaluación). Las demás (pruebas de la
automatización como el pleno 203, o la demo V004) se ven eligiéndolas en el filtro:

- **Gráfico** del porcentaje de tiempo de palabra de las mujeres y de la brecha de paridad (M04) en cada sesión.
- **Tabla resumen**: una fila por sesión con M01, M02, M02b, M03a, M03b, M04, M06, M09 y M13, en ese orden.
- **Lectura de la evolución**, con cifras calculadas por el código: compara solo las sesiones de
  control y nombra aparte las demás.
- Aviso: «Con 3 sesiones no se pueden sacar tendencias; el gráfico muestra cómo funcionará con más sesiones.»

## Lo que no debe hacer

- No mostrar caras ni fotogramas del vídeo.
- No hacer clasificaciones de personas concretas (por ejemplo, «quién habla menos»); las cifras se muestran por género.
- No ocultar `desconocido` ni el tiempo sin atribuir.
- No calcular cifras con el modelo de lenguaje: todas salen del código de `metrics/`.

## Cuándo está terminado

- Las dos pantallas y el botón de informe funcionan con los datos sintéticos (20 oct) y con las 3 sesiones reales (hecho el 23–26 oct, también en OVH).
- Hay al menos una prueba automática que comprueba que el panel carga una sesión sintética sin errores.
- Funciona en el portátil, sin GPU.
