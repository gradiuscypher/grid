.PHONY: setup dev worker test lint typecheck fmt migrate

setup:
	uv sync

dev:
	uv run uvicorn grid.main:app --host 0.0.0.0 --port 8000 --reload

worker:
	uv run python -m grid.workflows.worker

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

typecheck:
	uv run ty check

fmt:
	uv run ruff check --fix .
	uv run ruff format .

migrate:
	@echo "no migrations yet (Alembic lands in Phase 1)"
