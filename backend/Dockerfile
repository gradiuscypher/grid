FROM python:3.13-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

FROM base AS dev

COPY pyproject.toml README.md ./
RUN uv sync --no-install-project

COPY . .
RUN uv sync

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "grid.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
