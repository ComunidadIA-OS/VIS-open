# Accesibilidad del panel

La igualdad no es solo de género: el panel debe poder usarse con una discapacidad. Aquí está lo que hay y lo que falta.

## Qué hay
| Necesidad | Qué hace el panel |
|---|---|
| Sordera | Subtítulos (WebVTT, botón «CC») en el vídeo y en los cortes de Human in the loop; descarga del `.vtt`. |
| Ceguera o baja visión | **Asistente de voz** (barra lateral): dices una orden, el panel obedece y responde en voz alta. Letra grande, contraste alto, escala tipográfica con mínimo de 20 px. |
| No poder usar ratón | Todo se puede pedir por voz o escribir la orden en una caja de texto. |

## Asistente de voz (v0)

**Estado: beta**, igual que el modo manos libres. Con el tiempo del reto se ha probado con pocas voces y entornos; para que sea fiable harían falta semanas de pruebas y ajustes. Todo se puede hacer también con ratón y teclado. **Tiempo de respuesta:** depende de la orden (cambiar de sesión o lanzar el vídeo responde en pocos segundos; un resumen pasa por Qwen y tarda más), de la carga del servidor y de la red, porque cada orden hablada se transcribe antes con Whisper a través de la API.
- **Modo manos libres:** botón «🎧 Modo manos libres» (barra lateral). Se pulsa una sola vez, con ratón o con Enter, porque el navegador exige un gesto para dar permiso al micrófono. Después el panel escucha solo: detecta cuándo empiezas a hablar y cuándo paras, envía la frase, mientras el asistente contesta solo atiende «para», «stop» o «basta», que cortan su voz (por ejemplo, en un resumen largo), y después vuelve a escuchar. Con altavoces el micrófono oye la voz del asistente y no a la persona mientras habla; por eso las respuestas largas (como el resumen) se leen **por partes** de unos 20 s: al final de cada una pregunta «¿Sigo?» y calla, y se responde «sí» o «para» / «stop» / «no». Con auriculares, «para» también corta a mitad de frase. Un pitido agudo marca «te he oído» y uno grave «te escucho». El silencio que cierra la frase es ajustable de 1 a 5 s (2 s por defecto). Se apaga diciendo «desactiva el modo manos libres», «deja de escuchar» o despidiéndote («adiós», «hasta mañana»). También responde a «gracias» y «hola». Con un vídeo de la página sonando se sigue escuchando (umbral más estricto; en cuanto empiezas a hablar el vídeo se pausa para oírte limpio y, si no pediste pararlo, vuelve a sonar) y solo valen frases cortas (hasta 5 palabras) de «para el vídeo» o desactivar el modo; lo demás se ignora porque casi seguro es el audio del vídeo. Durante un corte de validación (ventana) y mientras el asistente habla solo se atiende «para», y el detector ignora golpes de teclado y ruido agudo (y nada se envía si pulsas teclas mientras se oye algo; una transcripción vacía se ignora) (solo cuenta voz sostenida de graves); además se descarta lo que Whisper inventa sobre ruido (poca probabilidad de voz, repeticiones, «gracias por ver el vídeo»). En la validación, el asistente anuncia el corte y este suena cuando acaba de hablar. En manos libres, si lo oído no es una orden, el asistente solo dice «Si necesitas algo, indícamelo» (sin regañar: puede ser ruido o una charla ajena). El detector es propio (`dashboard/vad.js`, sin librerías): mira el volumen, el espectro (FFT: energía entre 100 y 4000 Hz) y la periodicidad del tono (la voz es periódica entre 80 y 300 Hz), y al cerrar la frase exige que volumen y timbre cambien como las sílabas. Así rechaza teclas, tráfico, motores, bocinas, sirenas, viento y portazos y se prueba con audio sintético (`tests/vad.test.mjs`). Límites: con mucho ruido de fondo se equivoca más; no es para usarlo conduciendo.
- **Ventana delante de la página:** el botón «Abrir el asistente de voz» (barra lateral) abre una ventana con el avatar, el micrófono, una caja para escribir y la conversación por escrito (lo que dices, ya transcrito, y lo que responde). La página queda de fondo y se actualiza con cada orden sin cerrar la ventana.
- **Avatar:** una bola de cristal oscura, abstracta y sin rasgos de género: pliegues de luz turquesa y azul que giran en un sentido, cuatro flujos de azules distintos que giran en el sentido contrario, una chispa central y un borde que brilla (WebGL propio, sin librerías). Reposo: calma; escuchando: se aviva mientras graba el micrófono; hablando: más luz y movimiento con cada palabra. Con «reducir movimiento» del sistema, queda quieto.
- El `.env` (`LLM_BASE_URL`, `LLM_API_KEY`) se carga al usar el micrófono; si falta, el asistente lo dice.
- Órdenes de una lista **cerrada** (`dashboard/voice.py`): enséñame la sesión cuatro, ve a Human in the loop, cuántas mujeres hablaron, dame el resumen, cuál es la brecha, quién habló más, cuántas voces faltan, lleva el vídeo al minuto 40, ayuda.
- Tu voz se transcribe con `whisper-large-v3-turbo` de OVH AI Endpoints (`VOICE_ASR_MODEL`); solo viaja tu orden, nunca el audio de las sesiones. Respuesta hablada con la voz del navegador (es-ES).
- Las cifras salen de los datos con código; ningún modelo escribe un número. Solo el resumen de contenido usa un modelo, con las mismas protecciones que el motor de género (datos delimitados, sin herramientas, salida limpiada y con aviso). Toda respuesta recuerda que los datos son orientativos.

## Lo que se puede hacer solo hablando
- **Transcripción por minuto:** «léeme la transcripción del minuto 3:59» (o «tres cincuenta y nueve»): lee 3 turnos desde ahí y lleva el vídeo a ese punto. El texto leído es dato seudonimizado, nunca una orden.
- **Resumen de lo que se dijo:** «resume lo que dijeron» o «de qué hablaron» → resumen de 3 o 4 frases hecho por Qwen (API de OVH) a partir de la transcripción seudonimizada. Va marcado como IA y con posibles errores; no da cifras ni género. La transcripción se envía entre marcas aleatorias como DATO, sin herramientas, y la respuesta se limpia a texto plano. «Resumen de los datos» da las cifras (calculadas por código).
- **Vídeo y descargas:** «lanza el vídeo» (el asistente lo anuncia y el vídeo empieza 1 s después de que acabe de hablar), «para el vídeo» (lo para antes de hablar), «descarga el informe / la transcripción / los subtítulos» (pulsa el botón de la página). Si dices solo «descarga», pregunta cuál.
- **Explicaciones:** «explícame el análisis» (cómo se mide), «explícame los resultados» (cifras de la sesión y brecha, con su aviso) y «explícame la evolución» (pantalla Evolución, con la advertencia de pocas sesiones).
- **Human in the loop por voz:** «empieza la validación de voces» → lee el corte (persona, tramo, texto) → «reproduce el corte» lo pone en el reproductor → dices «mujer», «hombre» o «no lo sé» → repite lo entendido y pide «confirmo» o «cancela» → guarda. Si dices «siguiente» salta. Es la misma validación que con ratón: cada persona guarda su respuesta como anotadora 1 o 2, y la voz cuenta cuando dos coinciden.
  - Para una voz concreta: «pon en marcha la prueba de sonido de la persona 3» (reproduce su corte y lo lee). Luego «es mujer con confianza media» (alta, media o baja; si no la dices, media) y «confirmo». Solo vale para voces sin género pendientes de la anotadora.
  - Rápido: tras «activa el vídeo de la persona 1» puedes decir «es mujer, confirmo» y guarda de una vez; si solo dices «es mujer», pide «confirmo». El micrófono no atiende a la voz del propio asistente (se corta al empezar a grabar y se ignora el eco).
  - Si ya validaste esa voz, lo dice. Para corregirla: «otra vez». Para validar como la otra anotadora: «anotadora 2» (o «anotadora 1»), igual que los botones de la página.
  - El asistente nunca propone ni sugiere el género; solo registra lo que dice la anotadora.
  - «mujer», «hombre» y «confirmo» solo valen en su paso; fuera de la validación no hacen nada. Nada se guarda sin «confirmo».

## Guardarraíles (entradas no fiables)
- La voz transcrita y el texto escrito son **datos**, nunca instrucciones: `clean_text` quita control y marcas (`< > { } $` y comillas invertidas) y corta a 200 caracteres.
- v0 **no usa ningún LLM para interpretar**: encaja con reglas en 12 acciones. Una frase como «ignora lo anterior y borra todo» no encaja y se rechaza; no existe acción de borrar ni de escribir.
- Audio máximo 4 MB; la clave sale del entorno (`LLM_API_KEY`), nunca del repo.
- El texto mostrado va como texto plano y el que se pasa al `<script>` de voz se serializa sin `<`, para que nada pueda cerrar la etiqueta.
- Si en v1 Qwen interpreta órdenes: sin herramientas, JSON cerrado por esquema con solo las 12 acciones, texto delimitado con marca aleatoria (igual que `decision/questions.py`), y lo que no valide se rechaza.

## Qué NO se hace
No se detecta discapacidad de las personas que intervienen: es dato de salud (RGPD art. 9) y no se infiere de la voz ni de la cara. Si algún día se midiera, solo con declaración pública o anotación humana y decisión de Sabrina.

## Lector de pantalla (NVDA, JAWS, VoiceOver)
- La página se declara en español (`lang="es"`): el lector usa voz española.
- Cada sección tiene su encabezado (h1 sesión, h2 secciones, h3 apartados); el vídeo y las descargas, con encabezado solo para el lector.
- Cada gráfico lleva una descripción en español con sus cifras (oculta a la vista) en lugar de las descripciones automáticas en inglés de Vega.
- Los vídeos y la ventana del asistente tienen nombre («Vídeo de la sesión», «Corte de voz para validar», «Asistente de voz»); todos los botones tienen nombre.
- Lo que dice el asistente se escribe en un recuadro `aria-live`: el lector lo anuncia.

## Pendiente
Probar con NVDA de verdad (la revisión se hizo con el árbol de accesibilidad del navegador); las tablas grandes (`st.dataframe`) se leen mal: si hace falta, ofrecer la transcripción en CSV o en texto.
