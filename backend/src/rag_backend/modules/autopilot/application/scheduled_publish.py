"""Hand due ``scheduled`` runs to the publish job (AE-0370).

Instagram has no native scheduling and containers expire after 24 hours, so
nothing is sent to Graph while a run waits. When ``now >= scheduled_at`` the
run moves ``scheduled -> publishing`` (reason ``schedule_due``) and the
carousel is released public; the existing publish job then posts it (quota,
containers, Story, notice) on the same worker tick. The compare-and-set is
the idempotency key: a second tick finds the run no longer ``scheduled``. A
run whose carousel is no longer approved at its time expires instead, and
nothing is published.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

from rag_backend.modules.autopilot.constants import NOTICE_PUBLISH_FAILED
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.owner_ports import (
    CarouselReleaser,
    ReleaseCommand,
)
from rag_backend.modules.autopilot.domain.ports import (
    AutopilotRunRepository,
    CarouselPublishSnapshot,
    CarouselPublishSource,
    Clock,
    PublishCheckpoint,
    PublishNotifier,
)
from rag_backend.modules.autopilot.domain.publish import PublishNotice
from rag_backend.modules.autopilot.domain.schedule_ports import (
    DueScheduleQuery,
    ScheduledRunSource,
)
from rag_backend.modules.autopilot.schedule_constants import (
    LOG_SCHEDULE_DUE,
    REASON_SCHEDULE_DUE,
    REASON_SCHEDULE_RELEASE_FAILED,
    REASON_SCHEDULE_WITHDRAWN,
    SCHEDULE_SCAN_LIMIT,
)
from rag_backend.modules.editorial.public import WORKFLOW_STATUS_APPROVED_FOR_PUBLISH

logger = structlog.get_logger()

_S = AutopilotRunState


@dataclass(frozen=True, kw_only=True)
class ScheduledPublishDependencies:
    """Collaborators for one worker tick. The session is already bound."""

    runs: AutopilotRunRepository
    scheduled: ScheduledRunSource
    source: CarouselPublishSource
    release: CarouselReleaser
    notifier: PublishNotifier
    checkpoint: PublishCheckpoint
    clock: Clock


class ScheduledPublishSweep:
    """Move every due run to ``publishing``, or expire it when withdrawn."""

    def __init__(self, deps: ScheduledPublishDependencies) -> None:
        self._deps = deps

    async def tick(self) -> int:
        """Returns how many due runs moved. Each move is committed on its own."""
        now = self._deps.clock.now()
        query = DueScheduleQuery(now=now, limit=SCHEDULE_SCAN_LIMIT)
        moved = 0
        for run in await self._deps.scheduled.due(query):
            moved += await self._fire(run)
            await self._deps.checkpoint.commit()
        return moved

    async def _fire(self, run: AutopilotRun) -> int:
        snapshot = await self._snapshot(run)
        if not _still_approved(snapshot):
            return int(await self._move(run, _S.EXPIRED, REASON_SCHEDULE_WITHDRAWN))
        if not await self._move(run, _S.PUBLISHING, REASON_SCHEDULE_DUE):
            return 0
        logger.info(LOG_SCHEDULE_DUE, run_id=str(run.run_id))
        project_id = run.carousel_project_id or ""
        if await self._deps.release.release(ReleaseCommand(project_id=project_id)):
            return 1
        await self._release_failed(run)
        return 1

    async def _release_failed(self, run: AutopilotRun) -> None:
        """The carousel could not be made public: fail and tell the owner."""
        moved = await self._deps.runs.transition(
            TransitionCommand(
                run_id=run.run_id,
                expected=_S.PUBLISHING,
                new=_S.PUBLISH_FAILED,
                reason=REASON_SCHEDULE_RELEASE_FAILED,
            )
        )
        if not moved:
            return
        await self._deps.notifier.notify(
            PublishNotice(
                run_id=run.run_id,
                outcome=NOTICE_PUBLISH_FAILED,
                permalink=None,
                error_code=REASON_SCHEDULE_RELEASE_FAILED,
                offer_retry=False,
            )
        )

    async def _snapshot(self, run: AutopilotRun) -> CarouselPublishSnapshot | None:
        if run.carousel_project_id is None:
            return None
        return await self._deps.source.load(run.carousel_project_id)

    async def _move(
        self, run: AutopilotRun, new: AutopilotRunState, reason: str
    ) -> bool:
        return await self._deps.runs.transition(
            TransitionCommand(
                run_id=run.run_id, expected=_S.SCHEDULED, new=new, reason=reason
            )
        )


def _still_approved(snapshot: CarouselPublishSnapshot | None) -> bool:
    """False when the carousel is gone or was sent back or rejected."""
    if snapshot is None:
        return False
    return snapshot.workflow_status == WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
