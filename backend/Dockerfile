FROM python:3.11-slim AS base

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
COPY src/ src/
COPY README.md ./
RUN uv sync --frozen --no-dev

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# Install system dependencies for PostgreSQL (asyncpg) and Playwright browsers
RUN apt-get update && apt-get install -y --no-install-recommends curl libpq5 && rm -rf /var/lib/apt/lists/*

# Install Playwright browsers for carousel slide rendering (export phase)
RUN uv run playwright install chromium
RUN uv run playwright install-deps chromium

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "rag_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
