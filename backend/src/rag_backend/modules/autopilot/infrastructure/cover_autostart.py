"""The autopilot's auto-cover step: the consent gate in front of the facade.

The runner asks for one cover generation when a queued run starts a fresh
carousel. Without the owner's recorded consent (the ``AUTOPILOT_COVER_CONSENT``
switch) the step skips and logs before any photo is even read — none leaves
the app. The generation runs on its own session, so a failure can never break
the tick's session: the run is never affected by the cover.
"""

from __future__ import annotations

from collections.abc import Callable

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.cover_constants import (
    LOG_COVER,
    LOG_COVER_AUTO_SKIPPED,
    LOG_COVER_AUTO_STARTED,
    SKIP_COVER_NO_CONSENT,
)
from rag_backend.modules.editorial.public import (
    AutoCoverOutcome,
    schedule_autopilot_cover,
)

logger = structlog.get_logger()


class EditorialAutoCoverScheduler:
    """``AutoCoverScheduler``: one consent-gated cover job per fresh carousel."""

    def __init__(self, sessions: Callable[[], AsyncSession], *, consent: bool) -> None:
        self._sessions = sessions
        self._consent = consent

    async def start_cover(self, project_id: str) -> None:
        """Schedule the carousel's cover, or skip with a logged reason."""
        if not self._consent:
            _log_skip(project_id, SKIP_COVER_NO_CONSENT)
            return
        outcome = await self._run(project_id)
        if outcome is None:
            return
        if not outcome.scheduled:
            _log_skip(project_id, outcome.reason)
            return
        logger.info(
            LOG_COVER,
            outcome=LOG_COVER_AUTO_STARTED,
            project_id=project_id,
            generation_id=outcome.generation_id,
        )

    async def _run(self, project_id: str) -> AutoCoverOutcome | None:
        """The facade call on its own session; None when it crashed."""
        try:
            async with self._sessions() as session:
                return await schedule_autopilot_cover(session, project_id)
        except Exception:
            logger.exception(
                LOG_COVER, outcome=LOG_COVER_AUTO_SKIPPED, project_id=project_id
            )
            return None


def _log_skip(project_id: str, reason: str) -> None:
    logger.info(
        LOG_COVER,
        outcome=LOG_COVER_AUTO_SKIPPED,
        reason=reason,
        project_id=project_id,
    )


__all__ = ["EditorialAutoCoverScheduler"]
