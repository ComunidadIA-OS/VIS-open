.PHONY: test lint check pipeline

test:
	python -m pytest -q

lint:
	ruff check .

check: lint test

# Uso: make pipeline VIDEO=data/raw/debate.mp4 (requiere el extra [pipeline] y HF_TOKEN)
pipeline:
	python -m pipeline.run $(VIDEO)
