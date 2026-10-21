"""Idempotent Instagram publish for runs in ``publishing``.

One tick handles one run. ``ig_post_id`` makes a later tick a state
transition with no Graph call. A stored container younger than 24 hours
is polled and published instead of created again. The container id is
committed before ``media_publish`` so a crash resumes that container.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from rag_backend.domain.constants.instagram_publish import (
    ERR_INSTAGRAM_CONTAINER_FAILED,
    PUBLISH_RESULT_FAILED,
    PUBLISH_RESULT_PUBLISHED,
)
from rag_backend.modules.autopilot.application.publish_hold import (
    HeldAction,
    HeldRunCheck,
    HeldRunDependencies,
)
from rag_backend.modules.autopilot.application.publish_steps import (
    can_step,
    due_runs,
    gate_for,
    media_for,
    outcome_of,
    release_pending,
    reusable_container,
    should_record,
    stored_container,
)
from rag_backend.modules.autopilot.application.story_step import post_extras
from rag_backend.modules.autopilot.constants import (
    NOTICE_PUBLISH_FAILED,
    NOTICE_PUBLISHED,
    PUBLISH_MAX_ATTEMPTS,
    PUBLISH_SCAN_LIMIT,
    REASON_ATTEMPTS_EXHAUSTED,
    REASON_CAROUSEL_MISSING,
    REASON_CONTAINER_MISSING,
    REASON_IG_LOGIN_ABSENT,
    REASON_PUBLISHED,
    REASON_QUOTA_EXHAUSTED,
)
from rag_backend.modules.autopilot.domain.exceptions import InstagramCallError
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.ports import (
    AutopilotRunRepository,
    CarouselPublishSnapshot,
    CarouselPublishSource,
    Clock,
    InstagramGraphGateway,
    PublishCheckpoint,
    PublishNotifier,
)
from rag_backend.modules.autopilot.domain.publish import (
    CarouselMedia,
    ManualPublishOutcome,
    PublishAttemptCommand,
    PublishNotice,
    RunListQuery,
    SaveContainerCommand,
    SavePostCommand,
    StoredContainer,
    gate_reason,
)
from rag_backend.modules.autopilot.domain.publish_claims import PublishClaims, RunClaim
from rag_backend.modules.autopilot.domain.published_copy import with_late
from rag_backend.modules.autopilot.domain.schedule import late_minutes
from rag_backend.modules.autopilot.domain.story import StoryRunner
from rag_backend.modules.autopilot.recovery_constants import (
    MANUAL_CLAIM_STALE_MINUTES,
    NO_RETRY_REASONS,
    REASON_RELEASE_PENDING,
)


@dataclass(frozen=True, kw_only=True)
class PublishJobDependencies:
    """Collaborators for one publish job. One bundle keeps the constructor small.

    ``story`` posts the Story after the carousel; None means no Story step.
    """

    runs: AutopilotRunRepository
    source: CarouselPublishSource
    gateway: InstagramGraphGateway
    notifier: PublishNotifier
    clock: Clock
    checkpoint: PublishCheckpoint
    claims: PublishClaims
    story: StoryRunner | None = None


class SystemClock:
    """Production clock. Tests pass a fixed ``Clock`` instead."""

    def __init__(self) -> None:
        self._tz = UTC

    def now(self) -> datetime:
        """Current UTC time."""
        return datetime.now(self._tz)


class InstagramPublishJob:
    """Posts one approved carousel, or resumes the container from the last tick."""

    def __init__(self, deps: PublishJobDependencies) -> None:
        self._deps = deps
        self._held = HeldRunCheck(
            HeldRunDependencies(
                runs=deps.runs,
                gateway=deps.gateway,
                notifier=deps.notifier,
                clock=deps.clock,
                checkpoint=deps.checkpoint,
            )
        )

    async def tick(self) -> int:
        """Process at most one due ``publishing`` run. Returns 1 when it did.

        The run is claimed first, so the manual route cannot publish it at
        the same time (QA r1 H1).
        """
        query = RunListQuery(
            state=AutopilotRunState.PUBLISHING,
            limit=PUBLISH_SCAN_LIMIT,
        )
        runs = await self._deps.runs.list_by_state(query)
        for chosen in due_runs(runs, self._deps.clock.now()):
            if await self.claim(chosen):
                await self._claimed_tick(chosen)
                return 1
            if await self._took_over_held(chosen):
                return 1
        return 0

    async def _took_over_held(self, chosen: AutopilotRun) -> bool:
        """Resolve a run a dead worker's container holds (QA r3 Q2)."""
        action = await self._held.action_for(chosen)
        if action is HeldAction.WAIT:
            return False
        if not await self._deps.claims.take_over_held(self._run_claim(chosen)):
            return False
        if action is HeldAction.RESUME:
            await self._claimed_tick(chosen)
            return True
        try:
            await self._fail(chosen, ERR_INSTAGRAM_CONTAINER_FAILED, None)
        finally:
            await self._deps.claims.release_run(chosen.run_id)
        return True

    async def _claimed_tick(self, chosen: AutopilotRun) -> None:
        """A refused claim no longer blocks the next due run (QA r2 R4a)."""
        try:
            fresh = await self._deps.runs.get(chosen.run_id)
            if fresh is not None and fresh.state is AutopilotRunState.PUBLISHING:
                await self._execute(fresh, None)
        finally:
            await self._deps.claims.release_run(chosen.run_id)

    async def claim(self, run: AutopilotRun) -> bool:
        """Take the run's publish claim, or False when a fresh one is held."""
        return await self._deps.claims.claim_run(self._run_claim(run))

    def _run_claim(self, run: AutopilotRun) -> RunClaim:
        now = self._deps.clock.now()
        stale = now - timedelta(minutes=MANUAL_CLAIM_STALE_MINUTES)
        return RunClaim(run_id=run.run_id, now=now, stale_before=stale)

    async def publish_claimed(
        self, run: AutopilotRun, media: CarouselMedia
    ) -> ManualPublishOutcome:
        """Owner route on a claimed ``publishing`` run. Reuses its container."""
        if can_step(run, self._deps.gateway):
            return await self._execute(run, media)
        atomic = await self._deps.gateway.publish_atomic(media)
        post_id = atomic.post_id
        if post_id is not None and should_record(run, atomic.status, post_id):
            return await self._mark_published(run, post_id, None)
        return outcome_of(atomic.status, atomic.post_id, atomic.error_message)

    async def _execute(
        self,
        run: AutopilotRun,
        override: CarouselMedia | None,
    ) -> ManualPublishOutcome:
        if run.ig_post_id:
            return await self._mark_published(run, run.ig_post_id, run.ig_permalink)
        if run.publish_attempts >= PUBLISH_MAX_ATTEMPTS:
            reason = run.state_reason or REASON_ATTEMPTS_EXHAUSTED
            return await self._fail(run, reason, None)
        snapshot = await self._snapshot(run)
        media = media_for(snapshot, override)
        blocked = gate_reason(gate_for(snapshot, media))
        if blocked is not None or media is None:
            return await self._blocked(run, blocked or REASON_CAROUSEL_MISSING)
        return await self._publish(run, media)

    async def _blocked(self, run: AutopilotRun, reason: str) -> ManualPublishOutcome:
        """Fail on a pre-check, except while an approve is still releasing.

        An approved but not yet public carousel waits instead of failing.
        """
        if release_pending(run, reason, self._deps.clock.now()):
            return outcome_of(PUBLISH_RESULT_FAILED, None, REASON_RELEASE_PENDING)
        return await self._fail(run, reason, None)

    async def _publish(
        self, run: AutopilotRun, media: CarouselMedia
    ) -> ManualPublishOutcome:
        try:
            await self._ensure_quota()
            post_id = await self._container_then_publish(run, media)
        except InstagramCallError as exc:
            return await self._on_error(run, exc)
        await self._deps.runs.save_post(
            SavePostCommand(run_id=run.run_id, ig_post_id=post_id, ig_permalink=None)
        )
        await self._deps.checkpoint.commit()
        permalink = await self._permalink(post_id)
        return await self._mark_published(run, post_id, permalink)

    async def _container_then_publish(
        self, run: AutopilotRun, media: CarouselMedia
    ) -> str:
        now = self._deps.clock.now()
        stored = stored_container(run)
        container = await reusable_container(self._deps.gateway, stored, now)
        if container is None:
            container = await self._open(run, media)
        return await self._deps.gateway.finish_container(container)

    async def _open(self, run: AutopilotRun, media: CarouselMedia) -> StoredContainer:
        """Create the container and commit its id before ``media_publish``."""
        created_at = self._deps.clock.now()
        container_id = await self._deps.gateway.open_carousel(media)
        if not container_id:
            raise InstagramCallError(
                status_code=0,
                error_code=REASON_CONTAINER_MISSING,
                transient=False,
            )
        await self._deps.runs.save_container(
            SaveContainerCommand(
                run_id=run.run_id,
                container_id=container_id,
                created_at=created_at,
            )
        )
        await self._deps.checkpoint.commit()
        return StoredContainer(container_id=container_id, created_at=created_at)

    async def _ensure_quota(self) -> None:
        token = await self._deps.gateway.current_token()
        if not token or not self._deps.gateway.user_configured():
            raise InstagramCallError(
                status_code=0,
                error_code=REASON_IG_LOGIN_ABSENT,
                transient=False,
            )
        remaining = await self._deps.gateway.quota_remaining()
        if remaining <= 0:
            raise InstagramCallError(
                status_code=429,
                error_code=REASON_QUOTA_EXHAUSTED,
                transient=True,
            )

    async def _permalink(self, post_id: str) -> str | None:
        try:
            return await self._deps.gateway.permalink(post_id)
        except InstagramCallError:
            return None

    async def _on_error(
        self, run: AutopilotRun, exc: InstagramCallError
    ) -> ManualPublishOutcome:
        next_attempts = run.publish_attempts + 1
        if not exc.transient:
            return await self._fail(run, exc.error_code, None)
        if next_attempts < PUBLISH_MAX_ATTEMPTS:
            await self._deps.runs.record_attempt(
                PublishAttemptCommand(
                    run_id=run.run_id,
                    attempts=next_attempts,
                    reason=exc.error_code,
                    at=self._deps.clock.now(),
                )
            )
            await self._deps.checkpoint.commit()
            return outcome_of(PUBLISH_RESULT_FAILED, None, exc.error_code)
        return await self._fail(run, exc.error_code, next_attempts)

    async def _mark_published(
        self,
        run: AutopilotRun,
        post_id: str,
        permalink: str | None,
    ) -> ManualPublishOutcome:
        """Post the extras, then record the run as published.

        The Story runs before the transition, so a crash leaves the run publishing and
        the next tick resumes the Story; the Story never fails the post.
        """
        await self._deps.runs.save_post(
            SavePostCommand(
                run_id=run.run_id, ig_post_id=post_id, ig_permalink=permalink
            )
        )
        extras = with_late(
            await post_extras(self._deps.story, run.carousel_project_id),
            late_minutes(run.scheduled_at, self._deps.clock.now()),
        )
        changed = await self._deps.runs.transition(
            TransitionCommand(
                run_id=run.run_id,
                expected=AutopilotRunState.PUBLISHING,
                new=AutopilotRunState.PUBLISHED,
                reason=REASON_PUBLISHED,
            )
        )
        if changed:
            await self._deps.notifier.notify(
                PublishNotice(
                    run_id=run.run_id,
                    outcome=NOTICE_PUBLISHED,
                    permalink=permalink,
                    error_code=None,
                    offer_retry=False,
                    extras=extras,
                )
            )
        await self._deps.checkpoint.commit()
        return outcome_of(PUBLISH_RESULT_PUBLISHED, post_id, None)

    async def _fail(
        self,
        run: AutopilotRun,
        reason: str,
        attempts: int | None,
    ) -> ManualPublishOutcome:
        if attempts is not None:
            await self._deps.runs.record_attempt(
                PublishAttemptCommand(
                    run_id=run.run_id,
                    attempts=attempts,
                    reason=reason,
                    at=self._deps.clock.now(),
                )
            )
        changed = await self._deps.runs.transition(
            TransitionCommand(
                run_id=run.run_id,
                expected=AutopilotRunState.PUBLISHING,
                new=AutopilotRunState.PUBLISH_FAILED,
                reason=reason,
            )
        )
        if changed:
            await self._deps.notifier.notify(
                PublishNotice(
                    run_id=run.run_id,
                    outcome=NOTICE_PUBLISH_FAILED,
                    permalink=run.ig_permalink,
                    error_code=reason,
                    offer_retry=reason not in NO_RETRY_REASONS,
                )
            )
        await self._deps.checkpoint.commit()
        return outcome_of(PUBLISH_RESULT_FAILED, run.ig_post_id, reason)

    async def _snapshot(self, run: AutopilotRun) -> CarouselPublishSnapshot | None:
        if run.carousel_project_id is None:
            return None
        return await self._deps.source.load(run.carousel_project_id)


__all__ = [
    "InstagramPublishJob",
    "PublishJobDependencies",
    "SystemClock",
    "outcome_of",
]
