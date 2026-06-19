"""Shared Deep Agents harness — checkpointer provider (AE-0248).

Relocated from `bootstrap/app_factory.py` so both the carousel orchestrator and
(future) Deep Agent builders consume one composition surface. The carousel keeps
its single-writer checkpoint (keyed `thread_id=project_id`); the chat Deep Agents
get **no** checkpointer per ADR-0013 / AE-0247 (`message_repository` is canonical).
This is a behavior-preserving move — the body is byte-for-byte the prior
`_build_checkpointer`.
"""

from __future__ import annotations

from contextlib import AsyncExitStack
from pathlib import Path
from typing import Protocol

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()


class CheckpointerProvider(Protocol):
    """Builds a checkpointer, registering its cleanup on the given stack."""

    async def __call__(
        self, settings: Settings, stack: AsyncExitStack
    ) -> BaseCheckpointSaver | None: ...


async def _build_postgres_saver(
    settings: Settings, stack: AsyncExitStack
) -> BaseCheckpointSaver | None:
    if not settings.carousel_checkpoint_postgres_url:
        logger.warning(
            "carousel_checkpoint_postgres_missing_url",
            hint="set carousel_checkpoint_postgres_url or switch backend",
        )
        return None
    saver_pg = await stack.enter_async_context(
        AsyncPostgresSaver.from_conn_string(settings.carousel_checkpoint_postgres_url)
    )
    await saver_pg.setup()  # idempotent DDL for checkpoint tables
    return saver_pg


async def _build_sqlite_saver(
    settings: Settings, stack: AsyncExitStack
) -> BaseCheckpointSaver:
    if not settings.carousel_checkpoint_sqlite_path:
        return InMemorySaver()
    try:
        Path(settings.carousel_checkpoint_sqlite_path).parent.mkdir(
            parents=True, exist_ok=True
        )
        return await stack.enter_async_context(
            AsyncSqliteSaver.from_conn_string(settings.carousel_checkpoint_sqlite_path)
        )
    except Exception:
        logger.warning(
            "carousel_checkpoint_sqlite_fallback",
            hint="sqlite path not available, using memory",
        )
        return InMemorySaver()


async def build_checkpointer(
    settings: Settings, stack: AsyncExitStack
) -> BaseCheckpointSaver | None:
    """Construct the configured checkpointer, registering cleanup on the stack.

    Backend is selected via ``settings.carousel_checkpoint_backend``:
    sqlite (dev), postgres (prod), memory (ephemeral), disabled (no resume).
    """
    backend = settings.carousel_checkpoint_backend.lower()
    if backend == "disabled":
        return None
    if backend == "memory":
        return InMemorySaver()
    if backend == "postgres":
        return await _build_postgres_saver(settings, stack)
    return await _build_sqlite_saver(settings, stack)


__all__ = ["CheckpointerProvider", "build_checkpointer"]
