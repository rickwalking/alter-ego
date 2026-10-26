"""A database for the queue-flow integration tests: Postgres when available.

With ``DATABASE_URL`` on Postgres (CI) the tests run in a throwaway schema holding
the autopilot, carousel and generation-queue tables, with real foreign keys,
advisory locks and ``RETURNING``; otherwise on a SQLite file.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from rag_backend.infrastructure.database.config import Base
from tests.integration.pg_schema_support import PG_URL, isolated_schema

QUEUE_FLOW_TABLES = (
    "users",
    "persona_profiles",
    "quality_rubrics",
    "carousel_creator_assets",
    "carousel_projects",
    "topic_candidates",
    "autopilot_runs",
    "telegram_updates",
    "autopilot_served_urls",
    "generation_runs",
    "event_outbox",
    "workflow_audit_log",
)


def on_postgres() -> bool:
    """True when the tests run against Postgres."""
    return "postgresql" in PG_URL


@asynccontextmanager
async def queue_flow_engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """An engine on a fresh database holding the queue-flow tables."""
    if on_postgres():
        async with isolated_schema(QUEUE_FLOW_TABLES) as engine:
            yield engine
        return
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'queue_flow.db'}", poolclass=NullPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


__all__ = ["QUEUE_FLOW_TABLES", "on_postgres", "queue_flow_engine"]
