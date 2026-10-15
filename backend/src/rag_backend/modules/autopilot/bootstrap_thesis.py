"""Worker wiring for the POV thesis prompts (AE-0377, split from bootstrap)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.application.notifications import (
    NotificationDependencies,
)
from rag_backend.modules.autopilot.application.thesis_prompts import (
    ThesisPromptDependencies,
    ThesisPromptService,
)
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)


def thesis_prompts(
    db: AsyncSession, deps: NotificationDependencies
) -> ThesisPromptService:
    """The prompt service on the notify tick session and Telegram client."""
    repo = SqlAlchemyAutopilotRepository(db)
    return ThesisPromptService(
        ThesisPromptDependencies(
            runs=repo,
            topics=repo,
            notices=deps.notices,
            notifier=deps.notifier,
            chat_id=deps.chat_id,
            configured=deps.configured,
        )
    )


__all__ = ["thesis_prompts"]
