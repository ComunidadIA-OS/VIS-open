# Textos de licencias

VIS Open es **Apache-2.0** (`../LICENSE`, copia en `Apache-2.0.txt`). Aquí están los textos estándar de las demás licencias que aparecen en `THIRD_PARTY_LICENSES.md`, para quien quiera leerlos sin salir del repositorio.

| Licencia | Fichero | Componentes (resumen) |
|---|---|---|
| Apache-2.0 | `Apache-2.0.txt` | VIS Open; Streamlit, MediaPipe, OpenCV, Transformers, PEFT, Accelerate, Qwen3.5, tzdata |
| MIT | `MIT.txt` | Pydantic, faster-whisper, pyannote.audio, Whisper large-v3-turbo, modelos pyannote de segmentación y diarización 3.1, Systran faster-whisper |
| BSD-2-Clause | `BSD-2-Clause.txt` | WhisperX |
| BSD-3-Clause | `BSD-3-Clause.txt` | pandas, NumPy, Altair, PyAV, PyTorch (parte), ReportLab (variante BSD) |
| CC-BY-4.0 | `CC-BY-4.0.txt` | Modelo `wespeaker-voxceleb-resnet34-LM` y `speaker-diarization-community-1` de pyannote (exige atribución: ver `../NOTICE`) |

## Cómo leer esto

- Son los **textos estándar** de la lista SPDX (`spdx/license-list-data`, descargados el 21 oct 2026). En MIT y BSD quedan los huecos `<year>` y `<copyright holders>`: el aviso de copyright real es el de cada autor, que se ve en su repositorio o su paquete.
- **VIS Open no redistribuye ningún componente de terceros**: se instalan desde PyPI o se descargan en tiempo de ejecución. Estos textos son informativos; la obligación de atribución de CC-BY-4.0 se cumple en `../NOTICE`.
- FFmpeg (LGPL-2.1+) es un binario externo que no se distribuye con el repositorio.
- La licencia exacta y la fecha de verificación de cada componente están en `../THIRD_PARTY_LICENSES.md`. Si añades una dependencia, regístrala allí con la licencia **verificada en la fuente** y, si es de un tipo nuevo, añade su texto aquí.
