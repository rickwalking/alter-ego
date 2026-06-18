"""CLI entrypoint for the schema-vs-models drift check (AE-0207).

Run against a live database to fail (exit 1) when a mapped ORM column is missing
from the connected schema. Used by:

* the ``schema-drift`` backend gate (``scripts/ci/gates.sh``), and
* the deploy path (after ``alembic upgrade head``, before traffic is served).

Usage::

    DATABASE_URL=postgresql+asyncpg://... \
        uv run python -m rag_backend.infrastructure.database.check_drift_cli

Exit codes: 0 = no drift, 1 = drift detected, 2 = misconfiguration (no URL).
"""

from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine

from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.schema_drift import check_schema_drift

_DATABASE_URL_ENV = "DATABASE_URL"
_ASYNCPG_PREFIX = "postgresql+asyncpg://"
_PSYCOPG_PREFIX = "postgresql+psycopg://"
_AIOSQLITE_PREFIX = "sqlite+aiosqlite://"
_SQLITE_PREFIX = "sqlite://"

_ERR_NO_URL = (
    f"ERROR: {_DATABASE_URL_ENV} is not set — the drift check needs a live "
    "database connection."
)

_EXIT_OK = 0
_EXIT_DRIFT = 1
_EXIT_CONFIG = 2


def to_sync_url(database_url: str) -> str:
    """Convert an async SQLAlchemy URL to its sync driver equivalent."""
    if database_url.startswith(_ASYNCPG_PREFIX):
        return database_url.replace(_ASYNCPG_PREFIX, _PSYCOPG_PREFIX, 1)
    if database_url.startswith(_AIOSQLITE_PREFIX):
        return database_url.replace(_AIOSQLITE_PREFIX, _SQLITE_PREFIX, 1)
    return database_url


def main() -> int:
    """Run the drift check against ``DATABASE_URL``; return the process exit code."""
    # Import the models package so every table is registered on ``Base.metadata``.
    import rag_backend.infrastructure.database.models  # noqa: F401

    database_url = os.environ.get(_DATABASE_URL_ENV)
    if not database_url:
        print(_ERR_NO_URL, file=sys.stderr)
        return _EXIT_CONFIG

    engine = create_engine(to_sync_url(database_url))
    try:
        report = check_schema_drift(engine, Base.metadata)
    finally:
        engine.dispose()

    print(report.render())
    return _EXIT_DRIFT if report.has_drift else _EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
