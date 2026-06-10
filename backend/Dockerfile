FROM python:3.11-slim AS base

WORKDIR /app

RUN pip install --no-cache-dir uv

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libpq5 && \
    rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml backend/uv.lock ./
RUN mkdir -p src/rag_backend && touch src/rag_backend/__init__.py README.md
RUN uv sync --frozen --no-dev

COPY backend/src/ src/
COPY backend/alembic/ alembic/
COPY backend/alembic.ini ./
COPY skills/runtime/ /app/skills/runtime/
COPY README.md ./
RUN uv sync --frozen --no-dev

ENV ALTER_EGO_RUNTIME_SKILLS_ROOT=/app/skills/runtime

ENV PLAYWRIGHT_BROWSERS_PATH=/app/ms-playwright

RUN uv run playwright install chromium
RUN uv run playwright install-deps chromium

RUN addgroup --system --gid 1001 fastapi && \
    adduser --system --uid 1001 --home /app fastapi && \
    chown -R fastapi:fastapi /app

USER fastapi

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV PLAYWRIGHT_BROWSERS_PATH=/app/ms-playwright

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uv", "run", "uvicorn", "rag_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
