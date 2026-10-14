"""Owner-triggered Instagram publish (QA r1 H1).

* A carousel with an autopilot run is published only through that run, and
  only while it is ``publishing``; the run's post id short-circuits.
* A carousel without a run gets a ledger row whose post id short-circuits a
  second publish. Its container id is stored in that row before
  ``media_publish``, so a retry after a crash resumes or recovers that
  container instead of posting again (QA r2 R4b). The row is read again
  after the claim, so a container stored in between is resumed (QA r3 Q4).
* Both paths claim first, so the worker tick and a second request cannot
  call Graph for the same carousel at the same time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from rag_backend.domain.constants.instagram_publish import (
    PUBLISH_RESULT_FAILED,
    PUBLISH_RESULT_PUBLISHED,
)
from rag_backend.modules.autopilot.application.publish_job import (
    InstagramPublishJob,
    PublishJobDependencies,
)
from rag_backend.modules.autopilot.application.publish_steps import (
    outcome_of,
    reusable_container,
)
from rag_backend.modules.autopilot.domain.exceptions import (
    InstagramCallError,
    ManualPublishRefusedError,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRun, AutopilotRunState
from rag_backend.modules.autopilot.domain.publish import (
    AtomicPublishResult,
    CarouselMedia,
    ManualPublishCommand,
    ManualPublishOutcome,
    StoredContainer,
)
from rag_backend.modules.autopilot.domain.publish_claims import (
    ManualClaim,
    ManualContainer,
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
        # Another attempt may have written the ledger since the first read.
        record = await self._deps.claims.manual_record(project_id)
        if record is not None and record.ig_post_id:
            await self._deps.claims.finish_manual(record)
            return outcome_of(PUBLISH_RESULT_PUBLISHED, record.ig_post_id, None)
        if self._deps.gateway.can_resume():
            return await self._stepped(manual, _ledger_container(record))
        try:
            atomic = await self._deps.gateway.publish_atomic(manual.media)
        except Exception as exc:
            await self._deps.claims.finish_manual(_failed(project_id, str(exc), None))
            raise
        await self._deps.claims.finish_manual(_record(project_id, atomic))
        return outcome_of(atomic.status, atomic.post_id, atomic.error_message)

    async def _stepped(
        self, manual: _Manual, stored: StoredContainer | None
    ) -> ManualPublishOutcome:
        """Container first, committed, then ``media_publish`` (QA r2 R4b)."""
        project_id = manual.command.project_id
        now = self._deps.clock.now()
        container = stored
        try:
            container = await reusable_container(self._deps.gateway, stored, now)
            if container is None:
                container = await self._open(manual)
            post_id = await self._deps.gateway.finish_container(container)
        except InstagramCallError as exc:
            failed = _failed(project_id, exc.error_code, container)
            await self._deps.claims.finish_manual(failed)
            return outcome_of(PUBLISH_RESULT_FAILED, None, exc.error_code)
        except Exception as exc:
            await self._deps.claims.finish_manual(
                _failed(project_id, str(exc), container)
            )
            raise
        await self._deps.claims.finish_manual(
            _published(project_id, post_id, container)
        )
        return outcome_of(PUBLISH_RESULT_PUBLISHED, post_id, None)

    async def _open(self, manual: _Manual) -> StoredContainer:
        created_at = self._deps.clock.now()
        container_id = await self._deps.gateway.open_carousel(manual.media)
        await self._deps.claims.save_manual_container(
            ManualContainer(
                project_id=manual.command.project_id,
                container_id=container_id,
                created_at=created_at,
            )
        )
        return StoredContainer(container_id=container_id, created_at=created_at)

    def _claim(self, project_id: str) -> ManualClaim:
        now = self._deps.clock.now()
        return ManualClaim(
            project_id=project_id,
            now=now,
            stale_before=now - timedelta(minutes=MANUAL_CLAIM_STALE_MINUTES),
        )


def _record(project_id: str, atomic: AtomicPublishResult) -> ManualRecord:
    if atomic.status == PUBLISH_RESULT_PUBLISHED and atomic.post_id:
        return _published(project_id, atomic.post_id, None)
    return _failed(project_id, atomic.error_message or PUBLISH_RESULT_FAILED, None)


def _published(
    project_id: str, post_id: str, container: StoredContainer | None
) -> ManualRecord:
    return ManualRecord(
        project_id=project_id,
        state=MANUAL_STATE_PUBLISHED,
        ig_post_id=post_id,
        ig_permalink=None,
        error=None,
        ig_container_id=_container_id(container),
        ig_container_created_at=_created_at(container),
    )


def _failed(
    project_id: str, error: str, container: StoredContainer | None
) -> ManualRecord:
    """The failure keeps the container so a retry resumes it."""
    return ManualRecord(
        project_id=project_id,
        state=MANUAL_STATE_FAILED,
        ig_post_id=None,
        ig_permalink=None,
        error=error,
        ig_container_id=_container_id(container),
        ig_container_created_at=_created_at(container),
    )


def _ledger_container(record: ManualRecord | None) -> StoredContainer | None:
    if record is None or not record.ig_container_id:
        return None
    if record.ig_container_created_at is None:
        return None
    return StoredContainer(
        container_id=record.ig_container_id,
        created_at=record.ig_container_created_at,
    )


def _container_id(container: StoredContainer | None) -> str | None:
    return None if container is None else container.container_id


def _created_at(container: StoredContainer | None) -> datetime | None:
    return None if container is None else container.created_at
