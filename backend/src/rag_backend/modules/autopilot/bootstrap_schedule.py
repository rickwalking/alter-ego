"""Wire the scheduled-publish due sweep for one worker tick.

Kept beside ``bootstrap.py`` so that file stays under 400 lines.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.application.publish_job import SystemClock
from rag_backend.modules.autopilot.application.scheduled_publish import (
    ScheduledPublishDependencies,
    ScheduledPublishSweep,
)
from rag_backend.modules.autopilot.infrastructure.carousel_release import (
    PublishingCarouselReleaser,
)
from rag_backend.modules.autopilot.infrastructure.carousel_source import (
    PublishingCarouselSource,
)
from rag_backend.modules.autopilot.infrastructure.publish_notifier import (
    OutboxPublishNotifier,
)
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)
from rag_backend.modules.autopilot.infrastructure.schedule_store import (
    SqlScheduledRuns,
)


def scheduled_publish_sweep(
    session: AsyncSession, public_base_url: str
) -> ScheduledPublishSweep:
    """The due sweep on the tick's session."""
    repo = SqlAlchemyAutopilotRepository(session)
    return ScheduledPublishSweep(
        ScheduledPublishDependencies(
            runs=repo,
            scheduled=SqlScheduledRuns(session),
            source=PublishingCarouselSource(session, public_base_url),
            release=PublishingCarouselReleaser(session),
            notifier=OutboxPublishNotifier(session),
            checkpoint=repo,
            clock=SystemClock(),
        )
    )
