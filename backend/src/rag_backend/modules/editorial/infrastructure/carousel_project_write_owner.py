"""Single write owner for the workflow-owned ``carousel_projects`` fields (AE-0107).

Per the AE-0105 field-ownership map (§5.1) every *workflow-owned* (WO) column of
the legacy ``carousel_projects`` row has exactly one write owner. This module is
that owner — the legacy single-writer adapter: it is the **sole** place that
directly mutates the WO ORM columns (``status``, ``error_message``,
``current_phase``, ``phase_status``, ``workflow_status``,
``assigned_reviewer_id`` + the workflow-synced distribution copy) and the
**sole** caller of the ``lock_version`` resume compare-and-swap.

It is the write side of the legacy-carousel ACL — it lives in the editorial
module's infrastructure layer (alongside the AE-0109 ``LegacyCarouselAcl``) and
is exposed upward only through the editorial module's public facade. No editorial
routes are added in this phase (AE-0110). All other workflow writers (the
start/resume routes via the editorial workflow service, the editorial workflow
service phase sync, the background resume runner) route their WO writes through
this owner (via the facade), which commits through the platform Unit of Work
(``SqlAlchemyUnitOfWork``) — the single committer (ADR-0009 §9).

Behavior-preserving: the WO column values written here are byte-identical to the
pre-AE-0107 scattered writers; only the *ownership* and the *commit boundary* are
consolidated. The ``lock_version`` resume bump delegates unchanged to
:meth:`OptimisticLockService.bump_carousel_version` (the byte-identical resume
CAS), so its expected-version contract and its pairing with the
artifact-activation CAS (which keeps writing its own bump) are untouched.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.application.services.optimistic_lock_service import (
    CarouselVersionBumpParams,
    OptimisticLockService,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_STATUS_FAILED,
    WORKFLOW_STATE_LINKEDIN_POST_EN_KEY,
    WORKFLOW_STATE_LINKEDIN_POST_PT_KEY,
)
from rag_backend.domain.models import CarouselStatus
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.platform.database import SqlAlchemyUnitOfWork

# Workflow-state keys synced onto the legacy row's distribution columns. Pairs of
# (ORM column attribute, workflow-state key), kept identical to the pre-AE-0107
# ``_sync_project_phase`` body so the synced values stay byte-for-byte unchanged.
_DISTRIBUTION_SYNC_FIELDS: tuple[tuple[str, str], ...] = (
    ("caption", "caption"),
    ("blog_markdown", "blog_markdown"),
    ("linkedin_post_pt", WORKFLOW_STATE_LINKEDIN_POST_PT_KEY),
    ("linkedin_post_en", WORKFLOW_STATE_LINKEDIN_POST_EN_KEY),
)


class CarouselProjectWriteOwner:
    """Sole writer of the workflow-owned ``carousel_projects`` fields.

    Wraps the request-scoped session via the platform Unit of Work so the owner
    is also the single committer for the WO writes it stages. Mutation helpers
    only ``flush`` (staging the WO columns inside the open transaction); callers
    that previously called ``db.commit()`` for those fields now call
    :meth:`commit` (the UoW), keeping exactly one transaction owner per request.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._uow = SqlAlchemyUnitOfWork(session)

    async def commit(self) -> None:
        """Commit the WO writes staged in the request's transaction (UoW)."""
        await self._uow.commit()

    async def assign_reviewer(self, project_id: str, reviewer_id: str) -> None:
        """Stamp the workflow-owned ``assigned_reviewer_id`` (flush only)."""
        project = await self._session.get(CarouselProjectModel, project_id)
        if project is None:
            return
        project.assigned_reviewer_id = reviewer_id
        await self._session.flush()

    async def sync_phase(
        self,
        project_id: str,
        state: CarouselWorkflowState,
    ) -> None:
        """Sync the WO phase columns from workflow state for the Kanban board.

        Byte-identical to the legacy ``_sync_project_phase`` body: only ``flush``
        (the commit is owned by the caller via :meth:`commit`).
        """
        project = await self._session.get(CarouselProjectModel, project_id)
        if project is None:
            return
        project.current_phase = str(state.get("current_phase", project.current_phase))
        project.phase_status = str(state.get("phase_status", project.phase_status))
        if str(state.get("phase_status", "")) == PHASE_STATUS_FAILED:
            project.status = CarouselStatus.FAILED.value
        raw_workflow_status = state.get("workflow_status")
        if raw_workflow_status is not None:
            project.workflow_status = str(raw_workflow_status)
        for attr, key in _DISTRIBUTION_SYNC_FIELDS:
            val = state.get(key)
            if isinstance(val, str) and val.strip():
                setattr(project, attr, val)
        await self._session.flush()

    async def set_phase_status_and_commit(
        self,
        project_id: str,
        phase_status: str,
    ) -> None:
        """Set the WO ``phase_status`` and commit (background-runner path).

        The background resume runner mutates ``phase_status`` from a separate
        session; this owner serializes that write and owns its commit so no
        runner code touches the column or commits it directly. Byte-identical to
        the legacy runner: the commit is skipped when the project is absent.
        """
        project = await self._session.get(CarouselProjectModel, project_id)
        if project is None:
            return
        project.phase_status = phase_status
        await self.commit()

    async def bump_resume_lock_version(
        self,
        project_id: str,
        expected_version: int | None,
    ) -> int:
        """Run the resume ``lock_version`` compare-and-swap (flush only).

        Delegates UNCHANGED to ``OptimisticLockService.bump_carousel_version`` —
        the byte-identical resume CAS — so its expected-version contract and its
        pairing with the artifact-activation CAS (which keeps its own bump) are
        preserved exactly. The commit is owned by the caller via :meth:`commit`.
        """
        return await OptimisticLockService().bump_carousel_version(
            self._session,
            CarouselVersionBumpParams(
                project_id=project_id,
                expected_version=expected_version,
            ),
        )


__all__ = ["CarouselProjectWriteOwner"]
