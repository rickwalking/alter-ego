"""The web side of the generation queue: progress relay, queue health, alerts.

The web process runs no generation. It listens for the worker's SSE
events, reports the queue's numbers on ``/health/ready`` and pings Pedro through
the alerts bot when the worker is gone or the queue stalls.
"""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.bootstrap.autopilot_worker_factory import EngineFactory
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.database import config as database_config
from rag_backend.infrastructure.notifications.llm_alerts import TelegramLlmAlerts
from rag_backend.modules.generation_queue.public import (
    listen_for_progress,
    queue_health_check,
    run_queue_monitor,
)

_POSTGRESQL = "postgresql"
CHECK_NAME = "generation_queue"
STATUS_ERROR = "error"


async def _idle() -> None:
    """No relay or monitor off Postgres (SQLite dev and tests run no worker)."""


def _postgres_engine() -> AsyncEngine | None:
    engine = database_config.c_engine
    if engine is None or engine.dialect.name != _POSTGRESQL:
        return None
    return engine


def start_progress_relay(
    engine_factory: EngineFactory, stop: asyncio.Event
) -> asyncio.Task[None]:
    """Relay the worker's events into this process's SSE hub until ``stop``."""
    engine = _postgres_engine()
    if engine is None:
        return asyncio.create_task(_idle())
    return asyncio.create_task(listen_for_progress(engine, engine_factory, stop))


def start_queue_monitor(settings: Settings, stop: asyncio.Event) -> asyncio.Task[None]:
    """Watch the worker and the queue age until ``stop``."""
    engine = _postgres_engine()
    if engine is None:
        return asyncio.create_task(_idle())
    alerts = TelegramLlmAlerts(
        token=settings.telegram_alerts_bot_token.get_secret_value(),
        chat_id=settings.telegram_alerts_chat_id,
    )
    return asyncio.create_task(run_queue_monitor(engine, alerts.send, stop))


async def check_generation_queue(checks: dict[str, dict[str, str | int]]) -> None:
    """Add the queue's numbers to the readiness checks (never fails the probe)."""
    engine = database_config.c_engine
    if engine is None:
        return
    try:
        checks[CHECK_NAME] = await queue_health_check(engine)
    except Exception as exc:
        checks[CHECK_NAME] = {"status": STATUS_ERROR, "detail": type(exc).__name__}


__all__ = ["check_generation_queue", "start_progress_relay", "start_queue_monitor"]
