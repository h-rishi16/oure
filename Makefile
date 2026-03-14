# OURE Developer Workflow
VENV = .venv
BIN = $(VENV)/bin

.PHONY: install dev lint type test test-all build clean

install:
	$(BIN)/pip install -e .

dev:
	$(BIN)/pip install -e '.[dev,web]'
	$(BIN)/pre-commit install

lint:
	$(BIN)/ruff check oure/ tests/
	$(BIN)/ruff format --check oure/ tests/

type:
	$(BIN)/mypy oure/

test:
	$(BIN)/pytest tests/unit/ -v

test-all:
	$(BIN)/pytest tests/ -v --cov=oure --cov-report=term-missing

build:
	$(BIN)/python -m build

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache dist build oure.egg-info

