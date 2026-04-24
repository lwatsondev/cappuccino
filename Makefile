.PHONY: setup run test clean

TTY_FLAG := $(shell [ -t 0 ] || echo "-T")

setup:
	uv sync --all-groups
	uv run pre-commit install

run:
	docker compose -f docker/compose.yaml up --build

test:
	docker compose -f docker/compose.yaml --profile test run --build --rm $(TTY_FLAG) test

clean:
	docker compose -f docker/compose.yaml --profile test down --rmi local --volumes
	find docker/data -mindepth 2 -maxdepth 2 -exec rm -rf {} +
	find . -not -path './.venv/*' -name "*.pyc" -delete
	find . -not -path './.venv/*' -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache
