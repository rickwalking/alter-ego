"""Runs held in ``publishing`` by a container a dead worker left (QA r3 Q2).

``claim_run`` refuses a stale claim while a container younger than 24 hours
has no post id, because the dead holder may have published it. Instead of
waiting out those 24 hours silently, the job reads the container status once
per tick and acts on it:

- ``PUBLISHED``: take the claim over and recover the media (QA r2 R3 match).
- ``FINISHED``: take the claim over and call ``media_publish`` once.
- ``ERROR`` / ``EXPIRED``: take the claim over and fail the run.
- ``IN_PROGRESS`` (or an unreadable status): keep waiting.

A run held for more than 30 minutes is reported to the owner once.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from rag_backend.domain.constants.instagram_publish import (
    CONTAINER_STATUS_ERROR,
    CONTAINER_STATUS_EXPIRED,
    CONTAINER_STATUS_FINISHED,
    CONTAINER_STATUS_PUBLISHED,
)
from rag_backend.modules.autopilot.application.publish_steps import stored_container
from rag_backend.modules.autopilot.domain.exceptions import InstagramCallError
from rag_backend.modules.autopilot.domain.models import AutopilotRun
from rag_backend.modules.autopilot.domain.ports import (
    AutopilotRunRepository,
    Clock,
    InstagramGraphGateway,
    PublishCheckpoint,
    PublishNotifier,
)
from rag_backend.modules.autopilot.domain.publish import (
    PublishAttemptCommand,
    PublishNotice,
    StoredContainer,
)
from rag_backend.modules.autopilot.recovery_constants import (
    NOTICE_PUBLISH_HELD,
    PUBLISH_HELD_NOTICE_MINUTES,
    REASON_PUBLISH_HELD,
)


class HeldAction(StrEnum):
    """What the job does with a run a stale claim and a fresh container hold."""

    RESUME = "resume"
    FAIL = "fail"
    WAIT = "wait"


_ACTIONS: dict[str, HeldAction] = {
    CONTAINER_STATUS_PUBLISHED: HeldAction.RESUME,
    CONTAINER_STATUS_FINISHED: HeldAction.RESUME,
    CONTAINER_STATUS_ERROR: HeldAction.FAIL,
    CONTAINER_STATUS_EXPIRED: HeldAction.FAIL,
}


@dataclass(frozen=True, kw_only=True)
class HeldRunDependencies:
    """Collaborators the held-run check needs from the publish job."""

    runs: AutopilotRunRepository
    gateway: InstagramGraphGateway
    notifier: PublishNotifier
    clock: Clock
    checkpoint: PublishCheckpoint


class HeldRunCheck:
    """Reads a held run's container status and tells the owner about long holds."""

    def __init__(self, deps: HeldRunDependencies) -> None:
        self._deps = deps

    async def action_for(self, run: AutopilotRun) -> HeldAction:
        """RESUME, FAIL, or WAIT for a run whose claim was refused."""
        stored = stored_container(run)
        if stored is None or run.ig_post_id:
            return HeldAction.WAIT
        action = _ACTIONS.get(await self._status(stored), HeldAction.WAIT)
        if action is HeldAction.WAIT:
            await self._report_long_hold(run, stored)
        return action

    async def _status(self, stored: StoredContainer) -> str:
        try:
            return await self._deps.gateway.container_status(stored)
        except InstagramCallError:
            return ""

    async def _report_long_hold(
        self, run: AutopilotRun, stored: StoredContainer
    ) -> None:
        """One notice per run; ``state_reason`` remembers it was sent."""
        if run.state_reason == REASON_PUBLISH_HELD:
            return
        now = self._deps.clock.now()
        if now - stored.created_at <= timedelta(minutes=PUBLISH_HELD_NOTICE_MINUTES):
            return
        recorded = await self._deps.runs.record_attempt(
            PublishAttemptCommand(
                run_id=run.run_id,
                attempts=run.publish_attempts,
                reason=REASON_PUBLISH_HELD,
                at=now,
            )
        )
        if not recorded:
            return
        await self._deps.notifier.notify(
            PublishNotice(
                run_id=run.run_id,
                outcome=NOTICE_PUBLISH_HELD,
                permalink=None,
                error_code=REASON_PUBLISH_HELD,
                offer_retry=False,
            )
        )
        await self._deps.checkpoint.commit()


__all__ = ["HeldAction", "HeldRunCheck", "HeldRunDependencies"]
