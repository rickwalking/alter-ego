"""Worker wiring for the POV thesis prompts (split from bootstrap)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.application.notifications import (
    NotificationDependencies,
)
from rag_backend.modules.autopilot.application.publish_job import SystemClock
from rag_backend.modules.autopilot.application.queue_notices import (
    QueueNoticeDependencies,
    QueueNoticeService,
)
from rag_backend.modules.autopilot.application.thesis_prompts import (
    ThesisPromptDependencies,
    ThesisPromptService,
)
from rag_backend.modules.autopilot.infrastructure.backlog_store import SqlBacklogStore
from rag_backend.modules.autopilot.infrastructure.cover_offers import cover_offers
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)


def thesis_prompts(
    db: AsyncSession, deps: NotificationDependencies
) -> ThesisPromptService:
    """The prompt service on the notify tick session and Telegram client.

    The prompt previews the topic's GrokBot cover with its toggle.
    """
    repo = SqlAlchemyAutopilotRepository(db)
    return ThesisPromptService(
        ThesisPromptDependencies(
            runs=repo,
            topics=repo,
            notices=deps.notices,
            notifier=deps.notifier,
            chat_id=deps.chat_id,
            configured=deps.configured,
            covers=cover_offers(db),
        )
    )


def queue_notices(
    db: AsyncSession, deps: NotificationDependencies
) -> QueueNoticeService:
    """The approve-all summary and backlog notes on the notify tick session."""
    repo = SqlAlchemyAutopilotRepository(db)
    return QueueNoticeService(
        QueueNoticeDependencies(
            runs=repo,
            topics=repo,
            notices=deps.notices,
            notifier=deps.notifier,
            backlog=SqlBacklogStore(db),
            clock=SystemClock(),
            chat_id=deps.chat_id,
            configured=deps.configured,
        )
    )


__all__ = ["queue_notices", "thesis_prompts"]
