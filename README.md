# VIS Open

Herramienta abierta y local que mide la presencia, participación, protagonismo y representación de las mujeres en debates en vídeo (audio + gestos), sin reconocimiento facial. Reto "Mujeres por la IA Abierta" (SEDIA / Comunidad IA de Código Abierto). Equipo 6.

## Estado

M1 (16 oct 2026): estructura del repo, esquemas Pydantic de la línea de tiempo y de las tablas de revisión humana, CI y tests.

M2 (en curso, rama `m2-pipeline`): vídeo → audio 16 kHz mono (FFmpeg) → transcripción (faster-whisper + WhisperX) → diarización (pyannote) → `timeline.json` + un CSV de revisión por anotadora.

## Ejecutar el pipeline

Necesita FFmpeg en el PATH, Python < 3.14 (por WhisperX) y un token de Hugging Face con las condiciones de `pyannote/speaker-diarization-3.1` aceptadas.

```bash
pip install -e ".[pipeline]"
cp .env.example .env      # rellena HF_TOKEN; WHISPER_DEVICE=cuda en la VM
make pipeline VIDEO=data/raw/debate.mp4
```

La salida queda en `data/processed/<vídeo>/` (ignorado por git). El género de cada voz sale siempre como `desconocido`: lo anotan dos personas en `review_anotadora_1.csv` y `review_anotadora_2.csv`.

## Cómo probarlo

```bash
pip install -e ".[dev]"
make test     # tests
make check    # lint + tests
```

Requiere Python 3.11 o superior. Los tests usan solo datos sintéticos.

## Estructura

- `contracts/`: esquemas Pydantic (`AnalysisEvent`, `AnalysisTimeline`, `Speaker`, tablas de revisión y de gestos) y lectura/escritura de CSV.
- `pipeline/`: `audio.py`, `transcribe.py`, `diarize.py`, `timeline.py` y `run.py` (punto de entrada).
- `decision/`, `metrics/`, `evaluation/`, `dashboard/`, `docker/`: carpetas reservadas para M2 en adelante.
- `docs/`: documentación.
- `THIRD_PARTY_LICENSES.md`: dependencias y sus licencias.

## Principios

- El género nunca se infiere de la cara ni de la voz: lo anotan dos personas y se informa como género atribuido; `desconocido` siempre es visible.
- Todo en local. No se suben al repo audio, vídeo, transcripciones reales ni secretos.

## Licencia

Apache-2.0 (aprobada por Sabrina el 16 oct 2026; pendiente de avisar a Ivette y Veru). Ver `LICENSE`.
