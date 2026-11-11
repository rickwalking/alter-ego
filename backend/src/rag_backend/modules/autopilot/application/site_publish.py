"""Approve a carousel at final review for an Instagram publish from the site.

The owner's "Publicar agora" on the site works like the Telegram button: a
carousel with an autopilot run moves that run to ``publishing`` (approving the
final review and releasing the carousel), so the run's own publish path posts it
once; a carousel without a run only gets its final review approved. The caller
publishes afterwards. Every run move is a compare-and-set, so a Telegram tap and
a site click never both move the run.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from rag_backend.modules.autopilot.application.owner_approval import (
    FinalReviewApproval,
)
from rag_backend.modules.autopilot.application.owner_steps import (
    APPROVE_FAILED_STEP,
    APPROVE_REFUSED_STEP,
    APPROVE_STEP,
    OwnerStep,
)
from rag_backend.modules.autopilot.application.schedule_steps import (
    SCHEDULED_PUBLISH_NOW_STEP,
)
from rag_backend.modules.autopilot.domain.gate import ResumeStatus
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.ports import AutopilotRunRepository

_S = AutopilotRunState


@dataclass(frozen=True, kw_only=True)
class SitePublishDeps:
    """The runs and the final-review approval of one request."""

    runs: AutopilotRunRepository
    approval: FinalReviewApproval


class SitePublishApproval:
    """Make a final-review carousel publishable now, as "Publicar agora" does."""

    def __init__(self, deps: SitePublishDeps) -> None:
        self._deps = deps

    async def approve_for_publish(self, project_id: str) -> bool:
        """True when the carousel may be published now; False when refused.

        A run already ``publishing`` is published through its own claim; a
        generating, reworking, published or ended run is refused.
        """
        run = await self._deps.runs.find_by_carousel(project_id)
        if run is None:
            status = await self._deps.approval.approve_project(project_id)
            return status is ResumeStatus.APPLIED
        if run.state is _S.PUBLISHING:
            return True
        handlers: dict[_S, Callable[[AutopilotRun], Awaitable[bool]]] = {
            _S.AWAITING_OWNER: self._approve_run,
            _S.SCHEDULED: self._publish_scheduled,
        }
        handler = handlers.get(run.state)
        return await handler(run) if handler is not None else False

    async def _approve_run(self, run: AutopilotRun) -> bool:
        """Approve the final review, then release; a refused approve is undone."""
        if not await self._apply(run, APPROVE_STEP):
            return False
        status = await self._deps.approval.approve(run)
        if status is not ResumeStatus.APPLIED:
            await self._apply(run, APPROVE_REFUSED_STEP)
            return False
        return await self._release(run)

    async def _publish_scheduled(self, run: AutopilotRun) -> bool:
        """Already approved for a slot: publish now instead."""
        if not await self._apply(run, SCHEDULED_PUBLISH_NOW_STEP):
            return False
        return await self._release(run)

    async def _release(self, run: AutopilotRun) -> bool:
        if await self._deps.approval.release(run):
            return True
        await self._apply(run, APPROVE_FAILED_STEP)
        return False

    async def _apply(self, run: AutopilotRun, step: OwnerStep) -> bool:
        return await self._deps.runs.transition(
            TransitionCommand(
                run_id=run.run_id,
                expected=step.expected,
                new=step.new,
                reason=step.reason,
            )
        )


__all__ = ["SitePublishApproval", "SitePublishDeps"]
