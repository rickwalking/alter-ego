"""Request-scoped wiring for topic intake.

The clock override on ``app.state`` lets tests pin America/Sao_Paulo
midnight without touching the process clock.
"""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.infrastructure.config.settings import Settings, get_settings
from rag_backend.modules.autopilot.application.publish_job import SystemClock
from rag_backend.modules.autopilot.application.topic_intake import (
    TopicIntakeDependencies,
    TopicIntakeService,
)
from rag_backend.modules.autopilot.constants import APP_STATE_CLOCK
from rag_backend.modules.autopilot.domain.ports import Clock
from rag_backend.modules.autopilot.infrastructure.intake_store import (
    SqlAlchemyTopicIntakeStore,
)


def clock_from(request: Request) -> Clock:
    """Use the app-state clock when a test installed one."""
    override: object = getattr(request.app.state, APP_STATE_CLOCK, None)
    if override is None:
        return SystemClock()
    return cast(Clock, override)


def build_topic_intake(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TopicIntakeService:
    """Wire the intake service for this request."""
    deps = TopicIntakeDependencies(
        store=SqlAlchemyTopicIntakeStore(session),
        clock=clock_from(request),
        daily_cap=settings.autopilot_daily_cap,
    )
    return TopicIntakeService(deps)
