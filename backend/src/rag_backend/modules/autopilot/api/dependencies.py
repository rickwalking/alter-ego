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
from rag_backend.modules.autopilot.application.scout_failure import (
    ScoutFailureDependencies,
    ScoutFailureService,
)
from rag_backend.modules.autopilot.application.topic_intake import (
    TopicIntakeDependencies,
    TopicIntakeService,
)
from rag_backend.modules.autopilot.application.x_signals import (
    XSignalsDependencies,
    XSignalsService,
)
from rag_backend.modules.autopilot.constants import (
    APP_STATE_CLOCK,
    APP_STATE_SCOUT_NOTIFIER,
)
from rag_backend.modules.autopilot.domain.ports import Clock
from rag_backend.modules.autopilot.domain.scout_ports import StatusSender
from rag_backend.modules.autopilot.infrastructure.backlog_store import SqlBacklogStore
from rag_backend.modules.autopilot.infrastructure.cover_store import SqlCoverAssetStore
from rag_backend.modules.autopilot.infrastructure.intake_store import (
    SqlAlchemyTopicIntakeStore,
)
from rag_backend.modules.autopilot.infrastructure.scout_failure_log import (
    OutboxScoutFailureLog,
)
from rag_backend.modules.autopilot.infrastructure.scout_status import (
    ClosingTelegramStatus,
)
from rag_backend.modules.autopilot.infrastructure.telegram_notifier import AsyncSleeper
from rag_backend.modules.autopilot.infrastructure.x_signal_store import (
    SqlAlchemyXSignalStore,
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
    """Wire the intake service for this request.

    ``posts`` supplies the x-signals post texts that ``pov_news`` quotes cite;
    ``covers`` resolves the GrokBot covers the topics name; ``backlog`` keeps the
    themes the daily cap left out for the next morning.
    """
    store = SqlAlchemyTopicIntakeStore(session)
    deps = TopicIntakeDependencies(
        store=store,
        clock=clock_from(request),
        daily_cap=settings.autopilot_daily_cap,
        posts=store,
        covers=SqlCoverAssetStore(session),
        backlog=SqlBacklogStore(session),
    )
    return TopicIntakeService(deps)


def build_x_signals(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> XSignalsService:
    """Wire browser-signal intake for this request."""
    deps = XSignalsDependencies(
        store=SqlAlchemyXSignalStore(session),
        clock=clock_from(request),
    )
    return XSignalsService(deps)


def build_scout_failure(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ScoutFailureService:
    """Wire the scout-failed notifier. Tests may replace it on app state."""
    deps = ScoutFailureDependencies(
        notifier=_status_sender(request, settings),
        chat_id=settings.telegram_owner_chat_id,
        log=OutboxScoutFailureLog(session),
        clock=clock_from(request),
    )
    return ScoutFailureService(deps)


def _status_sender(request: Request, settings: Settings) -> StatusSender:
    override: object = getattr(request.app.state, APP_STATE_SCOUT_NOTIFIER, None)
    if override is not None:
        return cast(StatusSender, override)
    token = settings.telegram_bot_token.get_secret_value()
    return ClosingTelegramStatus(token, AsyncSleeper())
