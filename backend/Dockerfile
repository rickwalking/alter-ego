# syntax=docker/dockerfile:1
#
# Backend image — multi-stage (AE-0190), slim Playwright (AE-0191),
# BuildKit cache mounts (AE-0192). Build context is the repo root
# (docker-compose builds with `context: .`); see root .dockerignore (AE-0189).

# ---------------------------------------------------------------------------
# Builder: resolve and install dependencies into a self-contained /app/.venv.
# Nothing from this stage ships except the .venv copied into runtime.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /app

# Pinned uv from the official distroless image (reproducible, no `pip install uv`).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# UV_COMPILE_BYTECODE: precompile .pyc for faster cold starts.
# UV_LINK_MODE=copy: avoid hardlink warnings across the cache mount / layers.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install deps first (cache-friendly): only re-runs when pyproject/uv.lock change.
# The setuptools build backend needs the package tree present even for the
# dependency-only sync, so create a minimal stub of the project package + README.
COPY backend/pyproject.toml backend/uv.lock ./
RUN mkdir -p src/rag_backend && touch src/rag_backend/__init__.py README.md
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# ---------------------------------------------------------------------------
# Runtime: clean slim base, only the venv + app source + Chromium runtime.
# No uv, no pip, no build toolchain.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

# PLAYWRIGHT_BROWSERS_PATH must be identical in the layer that installs the
# browser and at runtime, so the app finds Chromium at the same location.
ENV PLAYWRIGHT_BROWSERS_PATH=/app/ms-playwright \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PATH=/app/.venv/bin:$PATH

# Create the non-root user FIRST so every COPY/RUN below can land files already
# owned by it. A trailing `chown -R /app` instead would duplicate the entire
# venv + Chromium tree into a ~1GB extra layer (Docker copy-on-write).
RUN addgroup --system --gid 1001 fastapi \
    && adduser --system --uid 1001 --home /app fastapi \
    && chown fastapi:fastapi /app

# Bring in the fully-resolved virtualenv from the builder, owned by the runtime
# user. The Playwright Python package lives here, so `playwright install` below
# uses the runtime venv.
COPY --from=builder --chown=fastapi:fastapi /app/.venv /app/.venv

# Playwright runtime (AE-0191): chromium browser + its OS deps in ONE layer,
# cleaned in the same RUN so the apt lists never persist into the image. The
# browser tree (~1GB) is chowned to the runtime user inside this same RUN, so it
# is owned where it is created (no duplicating chown layer afterwards).
# `curl`/`libpq5` are kept (healthcheck + libpq runtime for psycopg/asyncpg).
# AE-0191 (architect-validated): install ONLY the headless shell, not the full
# headed Chromium. Since Playwright v1.49 `install chromium` downloads BOTH the
# headed build AND chromium-headless-shell, and headless launches auto-use the
# shell. This app launches Chromium ONLY headless (playwright_export.py,
# research_tool.py) and never calls page.pdf() (PDFs are built by img2pdf from
# JPEGs), so the headed build is dead weight (~60-90MB). The apt `--with-deps`
# libs are shared and unchanged. VERIFY on staging: one carousel export renders
# pixel-identical (fonts/gradients/2x) before relying on this in prod.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl libpq5 \
    && playwright install --with-deps --only-shell \
    && chown -R fastapi:fastapi /app/ms-playwright \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Application source + runtime assets (only what the app needs at runtime),
# copied with ownership set so no post-copy recursive chown is required.
COPY --chown=fastapi:fastapi backend/src/ src/
COPY --chown=fastapi:fastapi frontend/public/about-pedro.jpg assets/about-pedro.jpg
COPY --chown=fastapi:fastapi backend/alembic/ alembic/
# Runtime skills (AE-0246) ship inside the backend package at
# rag_backend/agents/skills/, so they arrive via `COPY backend/src/ src/` above —
# no separate copy + no ALTER_EGO_RUNTIME_SKILLS_ROOT env needed.
COPY --chown=fastapi:fastapi backend/alembic.ini ./
COPY --chown=fastapi:fastapi README.md ./

USER fastapi

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# uvicorn is on PATH via /app/.venv/bin — no `uv run` indirection needed.
CMD ["uvicorn", "rag_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
