.PHONY: test lint check pipeline smoke synthetic

test:
	python -m pytest -q

lint:
	ruff check .

check: lint test

# Uso: make pipeline VIDEO=data/raw/debate.mp4 (requiere el extra [pipeline] y HF_TOKEN)
pipeline:
	python -m pipeline.run $(VIDEO)

# Uso: make smoke [AUDIO=ruta.wav]. Escribe data/smoke.json con tiempos y memoria (sin audio ni texto).
smoke:
	python -m pipeline.smoke $(AUDIO)
# Regenera los datos SINTÉTICOS de ejemplo (semilla fija) en evaluation/synthetic/muestras/
synthetic:
	python -m evaluation.synthetic
