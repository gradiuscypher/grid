.PHONY: setup dev worker test lint typecheck fmt migrate openapi-schema

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
	uv run alembic upgrade head

openapi-schema:
	uv run python -c "import json; from grid.main import app; print(json.dumps(app.openapi()))" > ../frontend/openapi.json
