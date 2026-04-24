"""TTL cleanup for carousel LangGraph checkpoints.

Deletes checkpoint threads for projects in COMPLETED or FAILED status
older than `settings.carousel_checkpoint_ttl_days`. Checkpoint tables
grow indefinitely otherwise — one thread per pipeline run, with
per-node rows, and the image_worker fan-out multiplies that.

Run as a cron job:
    uv run python scripts/cleanup_carousel_checkpoints.py
Or from a scheduler (Kubernetes CronJob, systemd timer, etc.).
"""

from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from datetime import UTC, datetime, timedelta
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from sqlalchemy import select

from rag_backend.domain.models import CarouselStatus
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.config import close_db, get_session, init_db
from rag_backend.infrastructure.database.models import CarouselProjectModel
from rag_backend.infrastructure.logging import get_logger, setup_logging

logger = get_logger()

FINISHED_STATUSES = (CarouselStatus.COMPLETED.value, CarouselStatus.FAILED.value)


async def _build_saver(settings: Any, stack: AsyncExitStack) -> BaseCheckpointSaver[Any] | None:
    backend = settings.carousel_checkpoint_backend.lower()
    if backend == "postgres":
        if not settings.carousel_checkpoint_postgres_url:
            return None
        return await stack.enter_async_context(
            AsyncPostgresSaver.from_conn_string(settings.carousel_checkpoint_postgres_url)
        )
    if backend == "sqlite":
        if not settings.carousel_checkpoint_sqlite_path:
            return None
        return await stack.enter_async_context(
            AsyncSqliteSaver.from_conn_string(settings.carousel_checkpoint_sqlite_path)
        )
    logger.warning("checkpoint_cleanup_unsupported_backend", backend=backend)
    return None


async def _collect_stale_thread_ids(cutoff: datetime) -> list[str]:
    """List carousel-{id} thread ids for projects finished before cutoff."""
    async for session in get_session():
        result = await session.execute(
            select(CarouselProjectModel.id).where(
                CarouselProjectModel.status.in_(FINISHED_STATUSES),
                CarouselProjectModel.updated_at < cutoff,
            )
        )
        return [f"carousel-{row[0]}" for row in result.fetchall()]
    return []


async def cleanup() -> int:
    """Reap stale checkpoint threads. Returns the count deleted."""
    settings = get_settings()
    setup_logging(debug=settings.debug)

    await init_db(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
    )

    deleted = 0
    try:
        async with AsyncExitStack() as stack:
            saver = await _build_saver(settings, stack)
            if saver is None:
                logger.info("checkpoint_cleanup_no_saver_configured")
                return 0

            cutoff = datetime.now(UTC) - timedelta(days=settings.carousel_checkpoint_ttl_days)
            thread_ids = await _collect_stale_thread_ids(cutoff)
            logger.info(
                "checkpoint_cleanup_targets",
                thread_count=len(thread_ids),
                cutoff=cutoff.isoformat(),
            )

            for thread_id in thread_ids:
                try:
                    await saver.adelete_thread(thread_id)
                    deleted += 1
                except Exception as exc:
                    logger.warning(
                        "checkpoint_cleanup_delete_failed",
                        thread_id=thread_id,
                        error=str(exc),
                    )
    finally:
        await close_db()

    logger.info("checkpoint_cleanup_done", deleted=deleted)
    return deleted


if __name__ == "__main__":
    asyncio.run(cleanup())
