"""Owner-triggered Instagram publish (QA r1 H1).

* A carousel with an autopilot run is published only through that run, and
  only while it is ``publishing``; the run's post id short-circuits.
* A carousel without a run gets a ledger row whose post id short-circuits a
  second publish.
* Both paths claim first, so the worker tick and a second request cannot
  call Graph for the same carousel at the same time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from rag_backend.domain.constants.instagram_publish import (
    PUBLISH_RESULT_FAILED,
    PUBLISH_RESULT_PUBLISHED,
)
from rag_backend.modules.autopilot.application.publish_job import (
    InstagramPublishJob,
    PublishJobDependencies,
    outcome_of,
)
from rag_backend.modules.autopilot.domain.exceptions import ManualPublishRefusedError
from rag_backend.modules.autopilot.domain.models import AutopilotRun, AutopilotRunState
from rag_backend.modules.autopilot.domain.publish import (
    AtomicPublishResult,
    CarouselMedia,
    ManualPublishCommand,
    ManualPublishOutcome,
)
from rag_backend.modules.autopilot.domain.publish_claims import (
    ManualClaim,
    ManualRecord,
)
from rag_backend.modules.autopilot.recovery_constants import (
    ERR_AUTOPILOT_RUN_ACTIVE,
    ERR_PUBLISH_IN_PROGRESS,
    MANUAL_CLAIM_STALE_MINUTES,
    MANUAL_STATE_FAILED,
    MANUAL_STATE_PUBLISHED,
)


@dataclass(frozen=True, kw_only=True)
class _Manual:
    command: ManualPublishCommand
    media: CarouselMedia


class ManualInstagramPublish:
    """The owner route's publish, idempotent per carousel."""

    def __init__(self, deps: PublishJobDependencies) -> None:
        self._deps = deps
        self._job = InstagramPublishJob(deps)

    async def publish(self, command: ManualPublishCommand) -> ManualPublishOutcome:
        """Publish once. Raises ``ManualPublishRefusedError`` before any Graph call."""
        media = CarouselMedia(caption=command.caption, image_urls=command.image_urls)
        manual = _Manual(command=command, media=media)
        run = await self._deps.runs.find_by_carousel(command.project_id)
        if run is not None:
            return await self._through_run(run, manual)
        return await self._without_run(manual)

    async def _through_run(
        self, run: AutopilotRun, manual: _Manual
    ) -> ManualPublishOutcome:
        if run.ig_post_id:
            return outcome_of(PUBLISH_RESULT_PUBLISHED, run.ig_post_id, None)
        if run.state is not AutopilotRunState.PUBLISHING:
            raise ManualPublishRefusedError(ERR_AUTOPILOT_RUN_ACTIVE)
        if not await self._job.claim(run):
            raise ManualPublishRefusedError(ERR_PUBLISH_IN_PROGRESS)
        try:
            return await self._claimed_run(run, manual)
        finally:
            await self._deps.claims.release_run(run.run_id)

    async def _claimed_run(
        self, run: AutopilotRun, manual: _Manual
    ) -> ManualPublishOutcome:
        fresh = await self._deps.runs.get(run.run_id)
        if fresh is not None and fresh.ig_post_id:
            return outcome_of(PUBLISH_RESULT_PUBLISHED, fresh.ig_post_id, None)
        if fresh is None or fresh.state is not AutopilotRunState.PUBLISHING:
            raise ManualPublishRefusedError(ERR_AUTOPILOT_RUN_ACTIVE)
        return await self._job.publish_claimed(fresh, manual.media)

    async def _without_run(self, manual: _Manual) -> ManualPublishOutcome:
        project_id = manual.command.project_id
        record = await self._deps.claims.manual_record(project_id)
        if record is not None and record.ig_post_id:
            return outcome_of(PUBLISH_RESULT_PUBLISHED, record.ig_post_id, None)
        if not await self._deps.claims.claim_manual(self._claim(project_id)):
            raise ManualPublishRefusedError(ERR_PUBLISH_IN_PROGRESS)
        try:
            atomic = await self._deps.gateway.publish_atomic(manual.media)
        except Exception as exc:
            await self._deps.claims.finish_manual(_failed(project_id, str(exc)))
            raise
        await self._deps.claims.finish_manual(_record(project_id, atomic))
        return outcome_of(atomic.status, atomic.post_id, atomic.error_message)

    def _claim(self, project_id: str) -> ManualClaim:
        now = self._deps.clock.now()
        return ManualClaim(
            project_id=project_id,
            now=now,
            stale_before=now - timedelta(minutes=MANUAL_CLAIM_STALE_MINUTES),
        )


def _record(project_id: str, atomic: AtomicPublishResult) -> ManualRecord:
    if atomic.status == PUBLISH_RESULT_PUBLISHED and atomic.post_id:
        return ManualRecord(
            project_id=project_id,
            state=MANUAL_STATE_PUBLISHED,
            ig_post_id=atomic.post_id,
            ig_permalink=None,
            error=None,
        )
    return _failed(project_id, atomic.error_message or PUBLISH_RESULT_FAILED)


def _failed(project_id: str, error: str) -> ManualRecord:
    return ManualRecord(
        project_id=project_id,
        state=MANUAL_STATE_FAILED,
        ig_post_id=None,
        ig_permalink=None,
        error=error,
    )
