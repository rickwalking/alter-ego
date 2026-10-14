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
    PUBLISH_RESULT_FAILED,
    PUBLISH_RESULT_PUBLISHED,
)
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
    DueFacts,
    ManualPublishOutcome,
    PublishAction,
    PublishAttemptCommand,
    PublishFacts,
    PublishGate,
    PublishNotice,
    RunListQuery,
    SaveContainerCommand,
    SavePostCommand,
    choose_publish_action,
    gate_reason,
    is_publish_due,
)
from rag_backend.modules.autopilot.domain.publish_claims import PublishClaims, RunClaim
from rag_backend.modules.autopilot.recovery_constants import MANUAL_CLAIM_STALE_MINUTES


@dataclass(frozen=True, kw_only=True)
class PublishJobDependencies:
    """Collaborators for one publish job. One bundle keeps the constructor small."""

    runs: AutopilotRunRepository
    source: CarouselPublishSource
    gateway: InstagramGraphGateway
    notifier: PublishNotifier
    clock: Clock
    checkpoint: PublishCheckpoint
    claims: PublishClaims


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
        chosen = _first_due(runs, self._deps.clock.now())
        if chosen is None or not await self.claim(chosen):
            return 0
        try:
            fresh = await self._deps.runs.get(chosen.run_id)
            if fresh is not None and fresh.state is AutopilotRunState.PUBLISHING:
                await self._execute(fresh, None)
        finally:
            await self._deps.claims.release_run(chosen.run_id)
        return 1

    async def claim(self, run: AutopilotRun) -> bool:
        """Take the run's publish claim, or False when a fresh one is held."""
        now = self._deps.clock.now()
        stale = now - timedelta(minutes=MANUAL_CLAIM_STALE_MINUTES)
        return await self._deps.claims.claim_run(
            RunClaim(run_id=run.run_id, now=now, stale_before=stale)
        )

    async def publish_claimed(
        self, run: AutopilotRun, media: CarouselMedia
    ) -> ManualPublishOutcome:
        """Owner route on a claimed ``publishing`` run. Reuses its container."""
        if _can_step(run, self._deps.gateway):
            return await self._execute(run, media)
        atomic = await self._deps.gateway.publish_atomic(media)
        post_id = atomic.post_id
        if post_id is not None and _should_record(run, atomic.status, post_id):
            return await self._mark_published(run, post_id, None)
        return _outcome(atomic.status, atomic.post_id, atomic.error_message)

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
        media = _media(snapshot, override)
        blocked = gate_reason(_gate(snapshot, media))
        if blocked is not None or media is None:
            failure = blocked or REASON_CAROUSEL_MISSING
            return await self._fail(run, failure, None)
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
        facts = PublishFacts(
            ig_post_id=run.ig_post_id,
            ig_container_id=run.ig_container_id,
            container_created_at=run.ig_container_created_at,
            now=self._deps.clock.now(),
        )
        action = choose_publish_action(facts)
        container_id = run.ig_container_id
        if action == PublishAction.CREATE_CONTAINER:
            container_id = await self._deps.gateway.open_carousel(media)
            await self._deps.runs.save_container(
                SaveContainerCommand(
                    run_id=run.run_id,
                    container_id=container_id,
                    created_at=self._deps.clock.now(),
                )
            )
            await self._deps.checkpoint.commit()
        if not container_id:
            raise InstagramCallError(
                status_code=0,
                error_code=REASON_CONTAINER_MISSING,
                transient=False,
            )
        return await self._deps.gateway.finish_container(container_id)

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
            return _outcome(PUBLISH_RESULT_FAILED, None, exc.error_code)
        return await self._fail(run, exc.error_code, next_attempts)

    async def _mark_published(
        self,
        run: AutopilotRun,
        post_id: str,
        permalink: str | None,
    ) -> ManualPublishOutcome:
        await self._deps.runs.save_post(
            SavePostCommand(
                run_id=run.run_id, ig_post_id=post_id, ig_permalink=permalink
            )
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
                )
            )
        await self._deps.checkpoint.commit()
        return _outcome(PUBLISH_RESULT_PUBLISHED, post_id, None)

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
                    offer_retry=True,
                )
            )
        await self._deps.checkpoint.commit()
        return _outcome(PUBLISH_RESULT_FAILED, run.ig_post_id, reason)

    async def _snapshot(self, run: AutopilotRun) -> CarouselPublishSnapshot | None:
        if run.carousel_project_id is None:
            return None
        return await self._deps.source.load(run.carousel_project_id)


def _first_due(runs: list[AutopilotRun], now: datetime) -> AutopilotRun | None:
    for run in runs:
        facts = DueFacts(
            attempts=run.publish_attempts, updated_at=run.updated_at, now=now
        )
        if is_publish_due(facts):
            return run
    return None


def _media(
    snapshot: CarouselPublishSnapshot | None,
    override: CarouselMedia | None,
) -> CarouselMedia | None:
    if override is not None:
        return override
    if snapshot is None:
        return None
    return CarouselMedia(caption=snapshot.caption, image_urls=snapshot.image_urls)


def _gate(
    snapshot: CarouselPublishSnapshot | None, media: CarouselMedia | None
) -> PublishGate:
    if snapshot is None:
        return PublishGate(
            project_found=False,
            base_url_configured=False,
            workflow_status="",
            status="",
            is_public=False,
            image_count=0,
        )
    count = len(snapshot.image_urls) if media is None else len(media.image_urls)
    return PublishGate(
        project_found=True,
        base_url_configured=snapshot.base_url_configured,
        workflow_status=snapshot.workflow_status,
        status=snapshot.status,
        is_public=snapshot.is_public,
        image_count=count,
    )


def _can_step(run: AutopilotRun | None, gateway: InstagramGraphGateway) -> bool:
    if run is None or run.state is not AutopilotRunState.PUBLISHING:
        return False
    return gateway.can_resume()


def _should_record(run: AutopilotRun | None, status: str, post_id: str | None) -> bool:
    if run is None or run.state is not AutopilotRunState.PUBLISHING:
        return False
    return status == PUBLISH_RESULT_PUBLISHED and post_id is not None


def outcome_of(
    status: str, post_id: str | None, error: str | None
) -> ManualPublishOutcome:
    """The HTTP-shaped outcome of one publish."""
    return _outcome(status, post_id, error)


def _outcome(
    status: str, post_id: str | None, error: str | None
) -> ManualPublishOutcome:
    return ManualPublishOutcome(status=status, ig_post_id=post_id, error_message=error)
