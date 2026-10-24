"""Run queued generation work in-process, the way the worker does.

The web routes only queue carousel work now. Integration tests that
drive a resume end to end hand the queued runs to the real job handler, without
PgQueuer (the handler is what PgQueuer would call) and without the drive lock
(SQLite has no advisory locks).
"""

from __future__ import annotations

from fastapi import FastAPI
from sqlalchemy import select

import rag_backend.infrastructure.database.config as db_config
from rag_backend.bootstrap.autopilot_worker_factory import autopilot_tick_config
from rag_backend.bootstrap.carousel_run_reaper_factory import (
    build_run_reaper_repository,
)
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.modules.autopilot.queue_bridge import AutopilotQueueBridge
from rag_backend.modules.autopilot.webhook_constants import APP_STATE_ENGINE
from rag_backend.modules.generation_queue.bootstrap import (
    HandlerParts,
    compose_handler,
)
from rag_backend.modules.generation_queue.constants import STATUS_QUEUED
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)
from rag_backend.worker.main import is_provider_error

MAX_ROUNDS = 20


async def run_queued_generation(app: FastAPI) -> int:
    """Handle every queued generation run until none is left; return how many."""
    settings = get_settings()
    engine = db_config.c_engine
    assert engine is not None
    sessions = db_config.get_session_maker()
    engine_factory = getattr(app.state, APP_STATE_ENGINE)
    handler = compose_handler(
        HandlerParts(
            engine=engine,
            sessions=sessions,
            bridge=AutopilotQueueBridge(
                config=autopilot_tick_config(settings, engine_factory),
                sessions=sessions,
                retryable=is_provider_error,
            ),
            reaper=build_run_reaper_repository(
                settings, app.state.carousel_checkpointer
            ),
            engine_factory=engine_factory,
            is_provider_error=is_provider_error,
            stopping=lambda: False,
        )
    )
    handled = 0
    for _ in range(MAX_ROUNDS):
        async with sessions() as session:
            queued = list(
                (
                    await session.scalars(
                        select(GenerationRunModel.id)
                        .where(GenerationRunModel.status == STATUS_QUEUED)
                        .order_by(GenerationRunModel.created_at)
                    )
                ).all()
            )
        if not queued:
            return handled
        for run_id in queued:
            await handler.handle(run_id)
            handled += 1
    return handled
