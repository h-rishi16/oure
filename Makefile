# OURE Developer Workflow

.PHONY: install dev lint type test build clean

install:
	pip install -e .

dev:
	pip install -e '.[dev,vis]'
	pre-commit install

lint:
	ruff check oure/ tests/
	ruff format --check oure/ tests/

type:
	mypy oure/

test:
	pytest tests/unit/ -v

test-all:
	pytest tests/ -v

build:
	python -m build

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache dist build
