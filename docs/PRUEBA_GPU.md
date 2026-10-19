# Prueba en la GPU de OVH (V100S)

Qué comprueba: que la imagen GPU arranca en la V100S, que PyTorch ve la tarjeta (arquitectura Volta, `sm_70`) y cuánto tardan y pesan la transcripción y la diarización con un audio corto. **Nada de esto se ha ejecutado todavía en OVH**: la imagen está escrita pero sin probar en GPU.

Reglas: sin audio real en el repo; el token de OVH y el de Hugging Face van solo en tu `.env` o en el entorno de la VM, nunca en el repo ni en la imagen.

## Antes de empezar

- En la VM: Docker, Docker Compose y el NVIDIA Container Toolkit (para que Docker vea la GPU). Comprueba con `nvidia-smi` en la VM y con:
  ```bash
  docker run --rm --gpus all python:3.12-slim-bookworm nvidia-smi
  ```
- Para entrar en la VM usa el token de OVH que ya tienes (no lo copies a ningún fichero del repo).
- Un token de Hugging Face con las condiciones de `pyannote/speaker-diarization-3.1` aceptadas. Sin él, el smoke omite la diarización y lo dice en el JSON.

## Pasos

1. Clona el repo en la VM y entra en la carpeta.
2. Crea el `.env` a partir del ejemplo y rellena `HF_TOKEN`:
   ```bash
   cp .env.example .env
   ```
   Para la GPU no hace falta tocar nada más (`WHISPER_DEVICE=cuda` y `float16` ya vienen en la imagen). Nunca `bfloat16`: Volta no lo tiene.
3. Construye la imagen GPU:
   ```bash
   docker compose -f docker/docker-compose.yml --profile gpu build gpu
   ```
4. (Opcional) Pon un audio corto, tuyo y fuera del repo, en `data/prueba.wav`. Sin audio, el smoke genera un tono sintético (sirve para medir arranque y memoria, no la calidad).
5. Ejecuta la prueba:
   ```bash
   docker compose -f docker/docker-compose.yml --profile gpu run --rm gpu                 # tono sintético
   docker compose -f docker/docker-compose.yml --profile gpu run --rm gpu python -m pipeline.smoke /data/prueba.wav
   ```
6. Lee `data/smoke.json` (no contiene texto ni audio) y pásalo al equipo.

## Qué mirar en `data/smoke.json`

| Campo | Qué significa |
|---|---|
| `cuda_available` | Debe ser `true`. Si es `false`, Docker no ve la GPU: revisa el Container Toolkit. |
| `gpu`, `gpu_compute_capability` | Debe salir la V100S y `7.0`. |
| `volta_sm70_supported` | Debe ser `true`. Si es `false`, la rueda de PyTorch no trae `sm_70`: reconstruye con otro `TORCH_INDEX_URL` (`--build-arg TORCH_INDEX_URL=...`, p. ej. un `cu1xx` anterior). |
| `steps.transcribe.seconds`, `steps.diarize.seconds` | Tiempo de cada paso para `audio_s` segundos de audio. |
| `peak_rss_mb`, `gpu_peak_mem_mb` | Memoria RAM máxima del proceso y memoria de GPU asignada por PyTorch. |
| `steps.diarize.status` | `omitido` = falta `HF_TOKEN`. |

## Si algo falla

- `ctranslate2` no encuentra cuDNN o cuBLAS: la imagen apunta `LD_LIBRARY_PATH` a las bibliotecas que trae PyTorch; si cambia la ruta, ajústala en `docker/Dockerfile`.
- El primer arranque descarga modelos (varios GB): se guardan en el volumen `models`, así que la segunda vez es rápido.
- No pegues el contenido de los PDF de OVH ni sus valores en incidencias ni en el chat; escribe solo "el token de OVH".

## Para probar en portátil (CPU)

```bash
docker compose -f docker/docker-compose.yml --profile cpu run --rm cpu
```
o, sin Docker, `make smoke`.
