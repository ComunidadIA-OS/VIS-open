# VIS Open

VIS Open es una herramienta de código abierto que mide la presencia y la participación de las mujeres en sesiones grabadas, a partir del audio y del vídeo, sin reconocimiento facial. El primer caso de uso son las sesiones del Congreso de los Diputados.

Proyecto del Equipo 6 en el reto «Mujeres por la IA Abierta» (SEDIA, Comunidad IA de Código Abierto).

## Qué hace

1. Toma una sesión del Congreso descargada sin modificar, con su ficha en el manifiesto (fuente, fecha y huella digital).
2. Extrae el audio, lo transcribe y separa a cada persona que habla.
3. Asigna a cada voz un código anónimo (Persona 1, Persona 2…) y su género **solo por pistas del lenguaje** («la señora…», «el señor…», «tiene la palabra…»), con la frase y el minuto como evidencia. No se guardan nombres: en la evidencia, el nombre se sustituye por el código. Si no hay pista, el género queda como `desconocido` y pasa a revisión humana.
4. Detecta en el vídeo las peticiones de palabra con la mano levantada, a partir de la postura del cuerpo y sin reconocer caras.
5. Calcula las métricas con código determinista y las muestra en un panel con el informe de cada sesión.

## Métricas de esta entrega

| ID | Qué mide | Cómo se calcula |
|---|---|---|
| M01 | Presencia: cuántas personas intervienen, por género | Código |
| M02 | Tiempo de palabra por persona y por género | Código |
| M03 | Número de turnos por género | Código |
| M04 | Brecha de paridad en el tiempo de palabra | Código |
| M13 | Porcentaje de tiempo sin atribuir | Código |
| M14 | Peticiones de palabra con la mano | Código, a partir del vídeo |
| M09 | Preguntas recibidas por cada persona | Modelo de lenguaje, con evidencia literal |

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
```

El vídeo debe tener su fila completa en el manifiesto (ver `docs/FUENTE_CONGRESO.md`); si no, no se analiza. Los resultados quedan en `data/processed/<vídeo>/`, que no se sube al repositorio.

## Estructura

- `contracts/`: formatos de datos comunes (línea de tiempo, voces, revisión humana y gestos).
- `pipeline/`: audio, transcripción, separación de voces, línea de tiempo, gestos y punto de entrada.
- `sources/`: fuente del Congreso y validación del manifiesto.
- `decision/`: género por pistas del lenguaje y motores de decisión (reglas o modelo de lenguaje).
- `metrics/`: registro y cálculo de las métricas.
- `evaluation/`: datos sintéticos y evaluación de los motores.
- `dashboard/`: panel en Streamlit con el informe de cada sesión y la evolución entre sesiones (ver `docs/PANEL.md`).
- `docker/`: imágenes para CPU y GPU.
- `docs/`: documentación (plan de trabajo, fichas de modelo y de datos, uso responsable, preguntas frecuentes).

## Principios

- El género nunca se deduce de la cara ni de la voz. Sale de pistas del lenguaje, de un dato declarado o de la revisión humana, y el informe indica siempre cómo se obtuvo. `desconocido` siempre es visible.
- Los vídeos del Congreso se usan sin alterar, citando la fuente y la fecha. Nunca se suben al repositorio.
- No se guardan nombres de personas: cada voz se identifica con un código anónimo (Persona 1, Persona 2…).
- No se suben al repositorio audio, vídeo, transcripciones reales ni claves.
- El sistema es agnóstico respecto al modelo de lenguaje: funciona con cualquier modelo abierto a través de una API compatible con OpenAI, y también sin modelo (motor de reglas).

## Componentes de terceros y licencias

La lista completa, con versiones y fuentes, está en [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md). Componentes principales:

| Componente | Uso | Licencia |
|---|---|---|
| faster-whisper | Transcripción | MIT |
| WhisperX | Alineado de palabras | BSD-2-Clause |
| pyannote.audio y `speaker-diarization-3.1` | Separación de voces | MIT (modelo de acceso restringido) |
| `wespeaker-voxceleb-resnet34-LM` | Huellas de voz para separar hablantes | CC-BY-4.0 |
| FFmpeg | Extracción de audio (binario externo) | LGPL-2.1+ |
| pandas | Métricas | BSD-3-Clause |
| Pydantic | Formatos de datos | MIT |
| OpenCV, MediaPipe, Streamlit, Qwen | Gestos, panel y modelo de lenguaje | Pendiente de verificar en la fuente antes de la entrega |

## Hoja de ruta

El plan detallado de esta entrega, con tareas, responsables, fechas y dependencias, está en [`docs/PLAN_DE_TRABAJO.md`](docs/PLAN_DE_TRABAJO.md).

Evolución futura:

- Pasar de 3 a 6–10 sesiones y, después, al archivo del Congreso, el Senado, el Parlamento Europeo, universidades y salas de conferencias.
- Más métricas: turno más largo, apertura y cierre, interrupciones, palabra cedida, distribución por cuartil, participación proporcional y tiempo en pantalla.
- Más métricas con IA: roles, temas y cortes de la Presidencia.
- Descarga automática de sesiones, una vez confirmado el permiso.
- Evaluación ampliada de la separación de voces con la métrica de Albayzin y el corpus Àgora, si su licencia lo permite.

## Equipo

Sabrina (dirección, arquitectura y modelo de IA), Ivette (definición y validación de métricas) y Veru (datos, métricas, panel y ética).

## Licencia

Apache-2.0. Ver [`LICENSE`](LICENSE).
