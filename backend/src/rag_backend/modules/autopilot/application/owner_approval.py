"""Approve final review and release the carousel for an owner tap.

Shared by publish-now and scheduling. A carousel whose workflow is
already ``approved_for_publish`` (a schedule the owner cancelled) is not
approved a second time.

The approve is bound to the revision of the message the owner tapped: the
editorial resume runs its lock-version compare-and-set at that revision, so a
review or reminder sent for an older render (slide 1 changed since, the new
review maybe not delivered yet) never approves the current one.
``current_revision`` lets the caller refuse before any run state moves.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.modules.autopilot.constants import GATE_FINAL_REVIEW
from rag_backend.modules.autopilot.domain.gate import (
    EditorialDriver,
    ResumeCommand,
    ResumeStatus,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRun
from rag_backend.modules.autopilot.domain.owner_ports import (
    CarouselReleaser,
    ReleaseCommand,
)
from rag_backend.modules.autopilot.domain.ports import CarouselPublishSource
from rag_backend.modules.editorial.public import (
    REVIEW_ACTION_APPROVE,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)


@dataclass(frozen=True, kw_only=True)
class FinalReviewApproval:
    """The editorial approve and the public release, for one request.

    Without ``carousels`` the approve is always sent.
    """

    editorial: EditorialDriver
    release_port: CarouselReleaser
    carousels: CarouselPublishSource | None = None

    async def current_revision(self, run: AutopilotRun) -> int | None:
        """The revision an approve must answer now; None when no approve is needed.

        An already approved carousel needs no approve: a slide-1 change drops
        the approval in the same commit, so its slide 1 is the approved one.
        """
        project_id = run.carousel_project_id or ""
        if await self._already_approved(project_id):
            return None
        return (await self.editorial.read_gate(project_id)).lock_version

    async def approve(
        self, run: AutopilotRun, revision: int | None = None
    ) -> ResumeStatus:
        """Approve final review once, at ``revision``. Already approved is applied.

        Without ``revision`` (no tapped message) the current lock version is used.
        """
        project_id = run.carousel_project_id or ""
        if await self._already_approved(project_id):
            return ResumeStatus.APPLIED
        if revision is None:
            revision = (await self.editorial.read_gate(project_id)).lock_version
        result = await self.editorial.resume(
            ResumeCommand(
                project_id=project_id,
                action=REVIEW_ACTION_APPROVE,
                expected_version=revision,
                feedback="",
                phase=GATE_FINAL_REVIEW,
            )
        )
        return result.status

    async def release(self, run: AutopilotRun) -> bool:
        """Make the carousel public. False when it is missing."""
        project_id = run.carousel_project_id or ""
        return await self.release_port.release(ReleaseCommand(project_id=project_id))

    async def _already_approved(self, project_id: str) -> bool:
        if self.carousels is None:
            return False
        snapshot = await self.carousels.load(project_id)
        if snapshot is None:
            return False
        return snapshot.workflow_status == WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
