# VIS Open

VIS Open es una herramienta de código abierto que mide la presencia y la participación de las mujeres en sesiones grabadas, a partir del audio y del vídeo, sin reconocimiento facial. El primer caso de uso son las sesiones del Congreso de los Diputados.

Proyecto del Equipo 6 en el reto «Mujeres por la IA Abierta» (SEDIA, Comunidad IA de Código Abierto).

## Qué hace

1. Toma una sesión del Congreso descargada sin modificar, con su ficha en el manifiesto (fuente, fecha y huella digital).
2. Extrae el audio, lo transcribe y separa a cada persona que habla.
3. Asigna a cada voz un código anónimo (Persona 1, Persona 2…) y su género **solo por pistas del lenguaje** («la señora…», «el señor…», «tiene la palabra…»), con la frase y el minuto como evidencia. No se guardan nombres: en la evidencia, el nombre se sustituye por el código. Si no hay pista, el género queda como `desconocido` y pasa a revisión humana.
4. Analiza el vídeo (personas visibles y tiempo en pantalla) a partir de la postura del cuerpo, sin reconocer caras ni deducir el género de la imagen.
5. Calcula las métricas con código determinista y las muestra en un panel con el informe de cada sesión (PDF, transcripción en CSV y subtítulos).
6. **Se puede usar sin ver la pantalla ni usar el ratón:** el panel tiene un asistente de voz y un modo manos libres (ver abajo).

## Panel, asistente de voz y accesibilidad

El panel (Streamlit, en local) es una sola página con tarjetas: vídeo de la sesión, **Human in the loop** (validar las voces sin género), métricas, análisis de audio y de vídeo y descargas. Además:

- **Asistente de voz:** una ventana con un avatar abstracto que obedece órdenes habladas o escritas de una **lista cerrada** («enséñame la sesión cuatro», «léeme la transcripción del minuto 3:59», «explícame los resultados», «lanza el vídeo», «descarga el informe»…). Las cifras que dice las calcula el código; el resumen del contenido lo hace Qwen y va marcado como IA.
- **Human in the loop por voz:** «activa el vídeo de la persona 1» reproduce el corte, tú dices «es mujer, confianza media» y «confirmo». El asistente nunca sugiere el género y **no guarda nada sin tu confirmación**.
- **Modo manos libres (innovación):** un clic y el panel escucha solo. Un **detector de voz propio** (`dashboard/vad.js`, sin librerías: espectro, tono y sílabas) separa la voz de las teclas, el tráfico, las bocinas y del audio del vídeo; se pausa mientras contesta y pausa el vídeo cuando hablas.
- **Accesibilidad:** subtítulos para personas sordas, voz y manos libres para personas ciegas o sin ratón, página en español con gráficos descritos para lectores de pantalla. Ver [`docs/DECLARACION_ACCESIBILIDAD.md`](docs/DECLARACION_ACCESIBILIDAD.md) y [`docs/ACCESIBILIDAD.md`](docs/ACCESIBILIDAD.md).

El audio de una orden hablada se transcribe con `whisper-large-v3-turbo` a través de una API compatible con OpenAI (OVHcloud AI Endpoints en el reto). Sin esa API el panel funciona igual: las órdenes se escriben. Qué datos salen del equipo y a quién: [`docs/PROVEEDORES.md`](docs/PROVEEDORES.md).

## Métricas de esta entrega

| ID | Qué mide | Cómo se calcula |
|---|---|---|
| M01 | Presencia: cuántas personas intervienen, por género | Código |
| M02 | Tiempo de palabra por género (con M02b, uso del tiempo asignado) | Código |
| M03a | Intervenciones por pregunta (control de calidad) | Código |
| M03b | Voces por pregunta (control de calidad) | Código |
| M04 | Brecha de paridad: % del tiempo de las mujeres menos su % entre quienes intervienen | Código |
| M06 | Preguntas a quien encabeza el Gobierno, por género de quien pregunta | Código, con el anuncio de la Presidencia |
| M09 | Preguntas recibidas por ministras y por ministros | Código, con el anuncio de la Presidencia; el modelo de lenguaje (Qwen) da el cargo al que va cada pregunta, con la cita literal |
| M13 | Porcentaje de tiempo sin atribuir (calidad del dato) | Código |

Definiciones completas en `docs/metricas.md`. **Validación** frente a la lista oficial de intervenciones del Congreso (3 sesiones, 87 personas): 86 con el género correcto, 0 errores y 1 a revisión humana; M06 coincide en las 3 sesiones y M09 en 2 de 3. Detalle en [`docs/EVALUACION.md`](docs/EVALUACION.md). Descartadas para el Congreso: M05, M08, M10 y M14–M16 (por ejemplo, en el pleno no se pide la palabra levantando la mano).

Las cifras las calcula siempre el código; el modelo de lenguaje solo clasifica frases (por ejemplo, si una intervención es una pregunta dirigida a alguien) y devuelve la frase que lo justifica. Si la muestra es insuficiente, la métrica se marca como «no concluyente».

## Instalación

Requisitos: Python 3.11 o superior (menor que 3.14 para el análisis de audio), FFmpeg en el PATH y, para la separación de voces, un token de Hugging Face con las condiciones de `pyannote/speaker-diarization-3.1` aceptadas.

```bash
pip install -e ".[dev]"        # código, pruebas y métricas
pip install -e ".[pipeline]"   # análisis de audio (en la máquina con GPU)
cp .env.example .env           # rellenar HF_TOKEN; WHISPER_DEVICE=cuda en la GPU
```

También hay imágenes Docker para CPU y para GPU en `docker/` (ver `docs/PRUEBA_GPU.md`).

## Uso

```bash
make pipeline VIDEO=data/raw/sesion.mp4   # analiza una sesión
make test                                 # pruebas con datos sintéticos
make check                                # estilo del código y pruebas
python -m sources.diputados                # composición de la cámara (M04 c), datos abiertos
python -m streamlit run dashboard/app.py  # el panel y el asistente de voz
python -m pipeline.sesion --buscar        # detecta y descarga los plenos nuevos (fila pendiente de validar)
python -m pipeline.sesion --pendientes    # analiza las sesiones validadas que falten
node tests/vad.test.mjs                   # prueba del detector de voz (necesita Node)
```

Para el asistente de voz hablado, en `.env`: `LLM_BASE_URL`, `LLM_API_KEY` y, opcional, `VOICE_ASR_MODEL` (por defecto `whisper-large-v3-turbo`). El resumen del contenido usa `LLM_MODEL`. Nada de esto va al repositorio.

El vídeo debe tener su fila completa en el manifiesto (ver `docs/FUENTE_CONGRESO.md`); si no, no se analiza. Los plenos nuevos se detectan solos con `--buscar`; las comisiones y los actos se añaden por enlace (`--congreso-url` o `--hls-url`). Flujo completo en [`docs/FLUJO.md`](docs/FLUJO.md). Los resultados quedan en `data/processed/<vídeo>/`, que no se sube al repositorio.

## Estructura

- `contracts/`: formatos de datos comunes (línea de tiempo, voces, revisión humana y gestos).
- `pipeline/`: audio, transcripción, separación de voces, línea de tiempo, gestos y punto de entrada.
- `sources/`: fuente del Congreso y validación del manifiesto.
- `decision/`: género por pistas del lenguaje y motores de decisión (reglas o modelo de lenguaje).
- `metrics/`: registro y cálculo de las métricas.
- `evaluation/`: datos sintéticos y evaluación de los motores.
- `dashboard/`: panel en Streamlit con el informe de cada sesión y la evolución entre sesiones (ver `docs/PANEL.md`); `voice.py` (órdenes de voz), `handsfree.py` y `vad.js` (modo manos libres y detector de voz), `avatar.py` (avatar del asistente).
- `docker/`: imágenes para CPU y GPU.
- `docs/`: documentación (plan de trabajo, fichas de modelo y de datos, uso responsable, proveedores, accesibilidad, borrador del plan RGPD y AI Act, preguntas frecuentes).

## Principios

- El género nunca se deduce de la cara ni de la voz. Sale de pistas del lenguaje, de un dato declarado o de la revisión humana, y el informe indica siempre cómo se obtuvo. `desconocido` siempre es visible.
- Los vídeos del Congreso se usan sin alterar, citando la fuente y la fecha. Nunca se suben al repositorio.
- No se guardan nombres de personas: cada voz se identifica con un código anónimo (Persona 1, Persona 2…).
- No se suben al repositorio audio, vídeo, transcripciones reales ni claves.
- El asistente de voz solo obedece una lista cerrada de órdenes, trata lo que oye como dato (nunca como instrucción), no guarda nada sin confirmación y marca como IA lo que genera un modelo.
- El sistema es agnóstico respecto al modelo de lenguaje: funciona con cualquier modelo abierto a través de una API compatible con OpenAI, y también sin modelo (motor de reglas).

## Componentes de terceros y licencias

La lista completa, con versiones, fuentes y fecha de verificación (última revisión: 21 oct 2026), está en [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md). Los textos de las licencias están en [`LICENSES/`](LICENSES/) y la atribución que exige CC-BY-4.0, en [`NOTICE`](NOTICE). VIS Open no redistribuye ningún componente: se instalan o se descargan desde sus fuentes. Componentes principales:

| Componente | Uso | Licencia |
|---|---|---|
| faster-whisper | Transcripción | MIT |
| WhisperX | Alineado de palabras | BSD-2-Clause |
| pyannote.audio y `speaker-diarization-3.1` | Separación de voces | MIT (modelo de acceso restringido) |
| `wespeaker-voxceleb-resnet34-LM` | Huellas de voz para separar hablantes | CC-BY-4.0 |
| FFmpeg | Extracción de audio (binario externo) | LGPL-2.1+ |
| pandas | Métricas | BSD-3-Clause |
| Pydantic | Formatos de datos | MIT |
| `whisper-large-v3-turbo` (vía API de OVHcloud) | Transcribir las órdenes de voz | MIT |
| Detector de voz, avatar y componentes del panel | Modo manos libres y asistente | Código propio (Apache-2.0); usa funciones del navegador (Web Audio, WebGL, síntesis de voz), sin librerías de terceros |
| OpenCV y MediaPipe | Análisis de vídeo (personas visibles, tiempo en pantalla) | Apache-2.0 |
| Streamlit y Altair | Panel y gráficos | Apache-2.0 y BSD-3-Clause |
| Qwen3.5 (4B y 9B) | Modelo de lenguaje (M09 y resumen) | Apache-2.0 |

## Hoja de ruta

El plan detallado de esta entrega, con tareas, responsables, fechas y dependencias, está en [`docs/PLAN_DE_TRABAJO.md`](docs/PLAN_DE_TRABAJO.md).

Evolución futura:

- **Automatización:** comprobar la detección automática con el primer pleno que se publique, de principio a fin: vídeo nuevo → manifiesto → validación humana → análisis. Ya está probada con el pleno 203 (ver [`docs/FLUJO.md`](docs/FLUJO.md)). Los plenos se detectan solos; los actos y las comisiones se añaden por enlace.
- **Ajuste ligero de Qwen** con una sesión de desarrollo (V008, 21/09/2022), distinta de las de evaluación, si mejora frente al modelo sin ajustar. La evaluación del modelo ya se hace con `modelo_por_pregunta` frente a la lista oficial de intervenciones.
- Pasar de 3 a 6–10 sesiones y, después, al archivo del Congreso, el Senado, el Parlamento Europeo, universidades y salas de conferencias.
- Más métricas (`docs/metricas.md`, evolución futura): interrupciones y llamadas al orden (M07), temas por género (M12), cortes de la Presidencia (M18) y M09 controlando el tema (el mismo ministerio con una ministra y con un ministro).
- Seudonimización: códigos por persona y no por palabra del nombre (hoy dos personas con un apellido en común comparten código).
- Análisis de vídeo en una máquina sin GPU o a la vez que la transcripción: bajaría el coste por pleno a la mitad (`docs/HERRAMIENTAS_Y_COSTES.md`).
- Asistente de voz: probarlo con lector de pantalla y con personas usuarias, más idiomas (catalán, francés) y una voz de síntesis mejor.
- Medir la transcripción (WER) y la separación de voces (DER) con un tramo de 5 min anotado a mano: el código está (`evaluation/asr_diar.py`), falta la anotación.
- Evaluación ampliada de la separación de voces con la métrica de Albayzin y el corpus Àgora, si su licencia lo permite.

## Equipo

Sabrina (dirección, arquitectura y modelo de IA), Ivette (definición y validación de métricas) y Veru (datos, métricas, panel y ética).

## Licencia

Apache-2.0. Ver [`LICENSE`](LICENSE), el aviso en [`NOTICE`](NOTICE) y los textos de las licencias de terceros en [`LICENSES/`](LICENSES/).
