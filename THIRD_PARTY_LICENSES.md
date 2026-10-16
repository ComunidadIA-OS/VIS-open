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
| pytest | 9.1.1 | desarrollo | MIT |
| ruff | 0.16.8 | desarrollo | MIT |
| pluggy, iniconfig, packaging, pygments | varias | desarrollo (dep. de pytest) | MIT, MIT, Apache-2.0 OR BSD-2-Clause, BSD-2-Clause |

## Pendientes de verificar (previstas, aún no instaladas)

faster-whisper, WhisperX, pyannote.audio (modelos con acceso restringido en Hugging Face: revisar condiciones), OpenCV, MediaPipe, pandas, Streamlit, FFmpeg (binario externo), llama.cpp / llama-server, Qwen3 (pesos), nimble / Laya (revisar; nunca nimble-v3), Docker.

## Licencia del proyecto

Apache-2.0: aprobada por Sabrina el 16 oct 2026.
