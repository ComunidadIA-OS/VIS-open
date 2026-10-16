.PHONY: test lint check

test:
	python -m pytest -q

lint:
	ruff check .

check: lint test
