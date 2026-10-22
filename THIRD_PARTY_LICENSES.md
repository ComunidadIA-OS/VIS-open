# Licencias de terceros

Regla: cada dependencia se registra aquí con la licencia verificada en el metadato del paquete instalado o en su repositorio, no de memoria. "Pendiente" = aún no verificada.

**Revisión del 21 oct 2026:** se volvieron a leer los metadatos de los paquetes instalados en el portátil (tablas de abajo, versiones al día) y la etiqueta de licencia de cada modelo en la API de Hugging Face. Los textos de las licencias están en [`LICENSES/`](LICENSES/) y las atribuciones que exige CC-BY-4.0, en [`NOTICE`](NOTICE). Los paquetes del extra `[pipeline]` y `[finetune]` (transformers, peft, accelerate, trl, datasets, whisperx) no están instalados en el portátil: su licencia es la verificada en PyPI y en el repositorio en la fecha de su fila.

## Verificadas (metadatos del paquete instalado, 16 oct 2026)

| Paquete | Versión | Uso | Licencia |
|---|---|---|---|
| pydantic | 2.14.1 | runtime | MIT |
| pydantic-core | 2.50.1 | runtime (dep. de pydantic) | MIT |
| annotated-types | 0.8.0 | runtime (dep. de pydantic) | MIT |
| typing-extensions | 4.16.0 | runtime (dep. de pydantic) | PSF-2.0 |
| typing-inspection | 0.4.4 | runtime (dep. de pydantic) | MIT |
| pandas | 3.0.5 | runtime (métricas) | BSD-3-Clause (texto de licencia en el metadato del paquete; clasificador «OSI Approved :: BSD License») |
| numpy | 2.5.1 | runtime (dep. de pandas) | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 (campo `License-Expression` del paquete) |
| python-dateutil | 2.9.0.post0 | runtime (dep. de pandas) | doble licencia BSD / Apache-2.0 (clasificadores del paquete) |
| tzdata | 2026.3 | runtime (dep. de pandas en Windows) | Apache-2.0 (metadato del paquete) |
| streamlit | 1.66.0 | panel (extra `[dashboard]`, también en `[dev]` para probarlo) | Apache-2.0 (campo `License-Expression` del paquete instalado) |
| altair | 6.3.0 | gráficos del panel (dep. de streamlit) | BSD-3-Clause (texto de licencia en el metadato; clasificador «OSI Approved :: BSD License») |
| openpyxl | 3.1.5 | hojas de anotación en Excel (extra `[anotacion]`; solo herramienta, no entra en el análisis) | MIT (campo `License` y clasificador OSI del paquete instalado, 22 oct 2026) |
| pytest | 9.1.1 | desarrollo | MIT |
| ruff | 0.17.1 | desarrollo | MIT |
| pluggy, iniconfig, packaging, pygments | varias | desarrollo (dep. de pytest) | MIT, MIT, Apache-2.0 OR BSD-2-Clause, BSD-2-Clause |

## Pipeline M2: verificadas en el repositorio oficial y en PyPI/Hugging Face (16 oct 2026)

Extra opcional `[pipeline]`: no se instala en CI ni en los portátiles; se usa en la VM de OVH.

| Componente | Versión (PyPI) | Uso | Licencia | Fuente |
|---|---|---|---|---|
| faster-whisper | 1.2.1 | transcripción | MIT | https://github.com/SYSTRAN/faster-whisper/blob/master/LICENSE |
| whisperx | 3.8.6 (requiere Python < 3.14) | alineado de palabras | BSD-2-Clause | https://github.com/m-bain/whisperX/blob/main/LICENSE |
| pyannote.audio | 4.0.7 | diarización | MIT | https://github.com/pyannote/pyannote-audio/blob/main/LICENSE |
| torch | 2.x (dep. de whisperx/pyannote) | runtime de modelos | BSD-3-Clause (archivo LICENSE); PyPI declara Apache-2.0 AND BSD-2/3-Clause AND MIT AND BSL-1.0 | https://github.com/pytorch/pytorch/blob/main/LICENSE |
| av (PyAV) | 18.1.0 (fijado `<19`) | decodificación de audio de faster-whisper | BSD-3-Clause (campo `License-Expression` del paquete instalado) | https://pypi.org/project/av/ |
| mediapipe | 1.1.1 | personas visibles y manos levantadas (extra `[video]`) | Apache-2.0 (campo `License` y clasificador del paquete instalado) | https://pypi.org/project/mediapipe/ |
| transformers | 5.20.2 | ajuste ligero de Qwen (extra `[finetune]`, solo en OVH) | Apache-2.0 (metadatos de PyPI) | https://pypi.org/project/transformers/ |
| peft | 0.21.2 | adaptador LoRA del ajuste (extra `[finetune]`) | Apache-2.0 (clasificador OSI de PyPI) | https://pypi.org/project/peft/ |
| accelerate | 1.15.0 | soporte del ajuste (extra `[finetune]`) | Apache-2.0 (clasificador OSI de PyPI) | https://pypi.org/project/accelerate/ |
| trl | 1.16.0 | instalado con el ajuste; el script usa un bucle propio (extra `[finetune]`) | Apache-2.0 (metadatos de PyPI) | https://pypi.org/project/trl/ |
| datasets | 5.1.0 | dependencia de trl (extra `[finetune]`) | Apache-2.0 (clasificador OSI de PyPI) | https://pypi.org/project/datasets/ |
| reportlab | 5.0.1 | informe descargable en PDF (extra `[dashboard]`) | BSD (campo `License` y clasificador OSI del paquete; la fuente Bitstream Vera que incluye permite redistribución) | https://pypi.org/project/reportlab/ |
| opencv-python-headless | 5.0.0.93 | lectura de fotogramas (extra `[video]`) | Apache-2.0 (campo `License` y clasificador del paquete instalado; la rueda incluye FFmpeg, LGPL) | https://pypi.org/project/opencv-python-headless/ |
| FFmpeg | binario externo, no se distribuye | extracción de audio | LGPL-2.1+ (GPL-2+ solo si se compila con `--enable-gpl`) | https://github.com/FFmpeg/FFmpeg/blob/master/LICENSE.md |

Modelos (se descargan en tiempo de ejecución, no se incluyen en el repo):

| Modelo | Uso | Licencia | Acceso |
|---|---|---|---|
| Systran/faster-whisper-small | transcripción en CPU (por defecto) | MIT (etiqueta de Hugging Face, 21 oct 2026) | libre |
| Systran/faster-whisper-large-v3 | transcripción en GPU (por defecto) | MIT (etiqueta de Hugging Face, 21 oct 2026). Su origen, `openai/whisper-large-v3`, declara **Apache-2.0** en su ficha; ambas permiten uso comercial y se cumplen conservando el aviso | libre |
| openai/whisper-large-v3-turbo | transcripción de las órdenes de voz del asistente, **solo por API** (OVHcloud AI Endpoints); no se descarga ni se redistribuye | **MIT** (etiqueta de la API de Hugging Face, 21 oct 2026) | libre |
| pyannote/speaker-diarization-3.1 | diarización (por defecto) | MIT (etiqueta de Hugging Face, 21 oct 2026) | restringido: aceptar condiciones en Hugging Face + `HF_TOKEN` |
| pyannote/segmentation-3.0 | usado por 3.1 | MIT | restringido |
| pyannote/wespeaker-voxceleb-resnet34-LM | embeddings de voz usados por 3.1 | CC-BY-4.0 (permite uso comercial; **exige atribución**, cumplida en `NOTICE`; etiqueta de Hugging Face, 21 oct 2026) | libre |
| pyannote/speaker-diarization-community-1 | alternativa (mejor DER), no usada por defecto | CC-BY-4.0 (atribución en `NOTICE`; etiqueta de Hugging Face, 21 oct 2026) | restringido |
| Qwen/Qwen3.5-4B y Qwen/Qwen3.5-9B | motor de preguntas y ajuste ligero (M09) | Apache-2.0 (etiqueta de la API de Hugging Face, 21 oct 2026) | libre |
| MediaPipe `pose_landmarker_full.task` (float16, 9 398 198 bytes, sha256 `4eaa5eb7…ec4ad`) | pose del cuerpo: personas visibles y manos levantadas | Apache-2.0 (ficha del modelo, verificada el 20 oct 2026). Límites de la ficha: modelo pensado para **una persona**, a menos de ~4 m; no apto para varias personas ni para reconocer identidad | libre (`POSE_MODEL`; `AUTO_DOWNLOAD=false`) |

La telemetría de pyannote.audio 4 se desactiva (`PYANNOTE_METRICS_ENABLED=0`).

Dependencias transitivas del extra (ctranslate2, transformers, nltk, omegaconf, torchaudio, etc.): pendiente de listar con sus licencias tras la primera instalación en la VM (`pip-licenses`).

## Pendientes de verificar (previstas, aún no instaladas)

llama.cpp / llama-server, nimble / Laya (revisar; nunca nimble-v3), Docker.

**Asistente de voz y manos libres (21 oct 2026):** no añaden dependencias de Python ni de JavaScript. El detector de voz (`dashboard/vad.js`), el avatar (shader WebGL) y el componente de Streamlit son código propio bajo Apache-2.0 y usan funciones del navegador (Web Audio, WebGL, síntesis de voz). Las frases de prueba de `tests/fixtures/voz/` son voz de síntesis de Windows, sin personas. Para grabar el vídeo de la demo se usó Playwright en un entorno aparte, que **no forma parte del repositorio**.

Imágenes Docker (rama `docker-gpu`, no distribuidas en el repo): `python:3.12-slim-bookworm` (Python: PSF; Debian: licencias por paquete) y las bibliotecas NVIDIA CUDA/cuDNN/cuBLAS que PyTorch instala como ruedas `nvidia-*`. **Pendiente de verificar en la fuente**: las ruedas `nvidia-*` llevan la licencia de NVIDIA (no OSI) y se descargan en tiempo de construcción, no se redistribuyen en el repo; Sabrina debe dar el visto bueno a esta dependencia.

## Interfaz del panel

El panel no carga fuentes, scripts ni estilos de terceros: usa las fuentes del sistema (`Iowan Old Style`, `Palatino`, `Georgia`…) y los recursos que Streamlit ya incluye (Apache-2.0, y su gráfico Vega a través de Altair, BSD-3-Clause). El detector de voz, el avatar y el componente del asistente son código propio.

## Licencia del proyecto

Apache-2.0: aprobada por Sabrina el 16 oct 2026. Texto en `LICENSE`; aviso en `NOTICE`; textos de las demás licencias en `LICENSES/`.
