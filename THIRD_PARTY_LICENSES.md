# Licencias de terceros

Regla: cada dependencia se registra aquí con la licencia verificada en el metadato del paquete instalado o en su repositorio, no de memoria. "Pendiente" = aún no verificada.

## Verificadas (metadatos del paquete instalado, 16 oct 2026)

| Paquete | Versión | Uso | Licencia |
|---|---|---|---|
| pydantic | 2.13.5 | runtime | MIT |
| pydantic-core | 2.46.5 | runtime (dep. de pydantic) | MIT |
| annotated-types | 0.8.0 | runtime (dep. de pydantic) | MIT |
| typing-extensions | 4.16.0 | runtime (dep. de pydantic) | PSF-2.0 |
| typing-inspection | 0.4.4 | runtime (dep. de pydantic) | MIT |
| pandas | 3.0.5 | runtime (métricas) | BSD-3-Clause (texto de licencia en el metadato del paquete; clasificador «OSI Approved :: BSD License») |
| numpy | 2.5.1 | runtime (dep. de pandas) | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 (campo `License-Expression` del paquete) |
| python-dateutil | 2.9.0.post0 | runtime (dep. de pandas) | doble licencia BSD / Apache-2.0 (clasificadores del paquete) |
| tzdata | 2026.3 | runtime (dep. de pandas en Windows) | Apache-2.0 (metadato del paquete) |
| streamlit | 1.66.0 | panel (extra `[dashboard]`, también en `[dev]` para probarlo) | Apache-2.0 (campo `License-Expression` del paquete instalado) |
| altair | 6.3.0 | gráficos del panel (dep. de streamlit) | BSD-3-Clause (texto de licencia en el metadato; clasificador «OSI Approved :: BSD License») |
| pytest | 9.1.1 | desarrollo | MIT |
| ruff | 0.16.8 | desarrollo | MIT |
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
| opencv-python-headless | 5.0.0.93 | lectura de fotogramas (extra `[video]`) | Apache-2.0 (campo `License` y clasificador del paquete instalado; la rueda incluye FFmpeg, LGPL) | https://pypi.org/project/opencv-python-headless/ |
| FFmpeg | binario externo, no se distribuye | extracción de audio | LGPL-2.1+ (GPL-2+ solo si se compila con `--enable-gpl`) | https://github.com/FFmpeg/FFmpeg/blob/master/LICENSE.md |

Modelos (se descargan en tiempo de ejecución, no se incluyen en el repo):

| Modelo | Uso | Licencia | Acceso |
|---|---|---|---|
| Systran/faster-whisper-small | transcripción en CPU (por defecto) | MIT | libre |
| Systran/faster-whisper-large-v3 | transcripción en GPU (por defecto) | MIT | libre |
| pyannote/speaker-diarization-3.1 | diarización (por defecto) | MIT | restringido: aceptar condiciones en Hugging Face + `HF_TOKEN` |
| pyannote/segmentation-3.0 | usado por 3.1 | MIT | restringido |
| pyannote/wespeaker-voxceleb-resnet34-LM | embeddings de voz usados por 3.1 | CC-BY-4.0 (permite uso comercial; exige atribución) | libre |
| pyannote/speaker-diarization-community-1 | alternativa (mejor DER), no usada por defecto | CC-BY-4.0 | restringido |
| MediaPipe `pose_landmarker_full.task` (float16, 9 398 198 bytes, sha256 `4eaa5eb7…ec4ad`) | pose del cuerpo: personas visibles y manos levantadas | Apache-2.0 (ficha del modelo, verificada el 20 oct 2026). Límites de la ficha: modelo pensado para **una persona**, a menos de ~4 m; no apto para varias personas ni para reconocer identidad | libre (`POSE_MODEL`; `AUTO_DOWNLOAD=false`) |

La telemetría de pyannote.audio 4 se desactiva (`PYANNOTE_METRICS_ENABLED=0`).

Dependencias transitivas del extra (ctranslate2, transformers, nltk, omegaconf, torchaudio, etc.): pendiente de listar con sus licencias tras la primera instalación en la VM (`pip-licenses`).

## Pendientes de verificar (previstas, aún no instaladas)

Streamlit, llama.cpp / llama-server, Qwen3 (pesos), nimble / Laya (revisar; nunca nimble-v3), Docker.

Imágenes Docker (rama `docker-gpu`, no distribuidas en el repo): `python:3.12-slim-bookworm` (Python: PSF; Debian: licencias por paquete) y las bibliotecas NVIDIA CUDA/cuDNN/cuBLAS que PyTorch instala como ruedas `nvidia-*`. **Pendiente de verificar en la fuente**: las ruedas `nvidia-*` llevan la licencia de NVIDIA (no OSI) y se descargan en tiempo de construcción, no se redistribuyen en el repo; Sabrina debe dar el visto bueno a esta dependencia.

## Licencia del proyecto

Apache-2.0: aprobada por Sabrina el 16 oct 2026.
