# Imagen del pipeline. Un solo Dockerfile para las dos variantes:
#   docker build -f docker/Dockerfile --target cpu -t vis-open:cpu .
#   docker build -f docker/Dockerfile --target gpu -t vis-open:gpu .
# Sin tokens ni secretos en la imagen: HF_TOKEN y el resto llegan por variables de entorno (.env).
FROM python:3.12-slim-bookworm AS base
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HF_HOME=/models PYANNOTE_METRICS_ENABLED=0
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY docker/constraints.txt pyproject.toml README.md ./
COPY contracts ./contracts
COPY pipeline ./pipeline

# --- CPU: torch de la rueda CPU (más pequeña) ---
FROM base AS cpu
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
ENV WHISPER_DEVICE=cpu
RUN pip install --extra-index-url ${TORCH_INDEX_URL} -c constraints.txt ".[pipeline]"
CMD ["python", "-m", "pipeline.smoke"]

# --- GPU: V100S (Volta, sm_70, sin bf16): float16 o int8 ---
FROM base AS gpu
# Cambia el índice si la rueda de torch deja de incluir sm_70; el smoke test lo comprueba.
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu126
ENV WHISPER_DEVICE=cuda WHISPER_COMPUTE_TYPE=float16
RUN pip install --extra-index-url ${TORCH_INDEX_URL} -c constraints.txt ".[pipeline]"
# ctranslate2 (faster-whisper) busca cuDNN/cuBLAS de CUDA 12 en esta ruta (vienen con torch).
ENV LD_LIBRARY_PATH=/usr/local/lib/python3.12/site-packages/nvidia/cudnn/lib:/usr/local/lib/python3.12/site-packages/nvidia/cublas/lib
CMD ["python", "-m", "pipeline.smoke"]
