"""Anti-corruption layer: legacy ``carousel_projects`` persistence ↔ editorial.

This module is the **single** seam between the editorial bounded context and the
legacy carousel persistence. It is the **only** file under
``rag_backend.modules.editorial`` that imports the carousel ORM / legacy carousel
persistence (``CarouselProjectModel``); the editorial application and domain
layers stay free of it (enforced by the AE-0112 import contract). Everything the
ACL exposes upward is in editorial terms (``EditorialProject`` /
``EditorialWorkflow``); everything it writes downward goes **through** the
AE-0107 :class:`CarouselProjectWriteOwner`, never by mutating the ORM row here.

**Read side.** Translates a session-attached ``CarouselProjectModel`` into the
editorial aggregate: the canonical :class:`CarouselProject` entity (via the
model's own ``to_entity`` — no second translator) wrapped with the
:class:`EditorialWorkflow` value object built from the legacy workflow columns
(``current_phase`` → ``phase``, ``phase_status``, ``workflow_status``). The
``lock_version`` optimistic-lock token is surfaced verbatim alongside the
aggregate so callers can read the concurrency token without touching the ORM.

**Write side.** The workflow-owned (WO) writes — reviewer assignment, the
phase/workflow-status sync from LangGraph state, the background-runner
phase-status set, and the resume ``lock_version`` compare-and-swap — are all
**delegated** to the injected :class:`CarouselProjectWriteOwner` (the AE-0107
single write owner). The ACL adds no persistence of its own and never calls
``session.add`` / ``flush`` / ``commit`` on the carousel row, so the owner stays
the sole writer and the single committer for those fields.

**Behavior-preserving (AE-0109).** No routes are moved (AE-0110), no schema
changes, no second persistence translator, and no workflow/agent behavior
change. The ``lock_version`` semantics and the LangGraph checkpoint identifier
(``thread_id == project_id``) are passed through unchanged: the ACL never
rewrites an id and never bumps the lock outside the owner's byte-identical resume
CAS.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.editorial.domain.models import (
    EditorialProject,
    EditorialWorkflow,
)
from rag_backend.modules.editorial.infrastructure.carousel_project_write_owner import (
    CarouselProjectWriteOwner,
)

if TYPE_CHECKING:
    from rag_backend.application.services.carousel.editorial_workflow_types import (
        EditorialWorkflowStartInput,
    )
    from rag_backend.modules.editorial.application.workflow_handlers import (
        WorkflowEngine,
    )

# Default optimistic-lock token for a row whose ``lock_version`` is unset, kept
# identical to the legacy reads (``int(model.lock_version or 1)``) so the token
# the ACL surfaces matches what the resume CAS expects.
_DEFAULT_LOCK_VERSION = 1


@dataclass(frozen=True)
class EditorialProjectView:
    """An editorial aggregate plus its legacy concurrency token.

    Surfaces the :class:`EditorialProject` (editorial terms only) together with
    the legacy ``lock_version`` optimistic-lock token read verbatim from the row.
    Callers read the token through this view instead of touching the carousel
    ORM, keeping the ACL the only carousel-persistence importer.
    """

    project: EditorialProject
    lock_version: int

    @property
    def checkpoint_thread_id(self) -> str:
        """The LangGraph checkpoint ``thread_id`` (== the project id, verbatim).

        The carousel workflow keys its LangGraph checkpoints by ``thread_id =
        project_id``; the ACL exposes that identifier unchanged so callers never
        derive a different key.
        """
        return str(self.project.project.id)


class LegacyCarouselAcl:
    """Translate legacy carousel persistence to/from editorial concepts.

    The ACL binds the request-scoped session (for reads) and the AE-0107
    :class:`CarouselProjectWriteOwner` (for all WO writes). It performs no
    persistence of its own: reads go through the ORM model's existing
    ``to_entity`` translator, and every write is delegated to the owner so the
    owner stays the single writer + single committer for the WO columns.
    """

    def __init__(
        self,
        session: AsyncSession,
        write_owner: CarouselProjectWriteOwner,
    ) -> None:
        self._session = session
        self._write_owner = write_owner

    # --- Read side: legacy row -> editorial aggregate --------------------------
    @staticmethod
    def to_editorial(model: CarouselProjectModel) -> EditorialProjectView:
        """Map a legacy ``CarouselProjectModel`` to the editorial aggregate.

        Reuses the model's canonical ``to_entity`` (no second translator) for the
        :class:`CarouselProject`, derives the :class:`EditorialWorkflow` from the
        legacy workflow columns, and surfaces the ``lock_version`` token verbatim.
        """
        project = model.to_entity()
        workflow = EditorialWorkflow(
            phase=str(model.current_phase),
            phase_status=str(model.phase_status),
            workflow_status=str(model.workflow_status or ""),
        )
        return EditorialProjectView(
            project=EditorialProject(project=project, workflow=workflow),
            lock_version=int(model.lock_version or _DEFAULT_LOCK_VERSION),
        )

    async def load_editorial(self, project_id: str) -> EditorialProjectView | None:
        """Load the editorial aggregate for a project, or ``None`` if absent.

        Reads the session-attached legacy row by primary key (the project id is
        the LangGraph checkpoint ``thread_id``, unchanged) and translates it.
        """
        model = await self._session.get(CarouselProjectModel, project_id)
        if model is None:
            return None
        return self.to_editorial(model)

    # --- Engine binding: run the wrapped engine over the bound session --------
    async def get_workflow_state_with_session(
        self,
        engine: WorkflowEngine,
        project_id: str,
    ) -> CarouselWorkflowState | None:
        """Read engine state with the request session bound (in_progress merge).

        The ACL is the only seam allowed to hand the engine the request session,
        so the engine's ``db``-says-in_progress merge stays byte-identical while
        the route/handler never touch the raw ``AsyncSession``. The LangGraph
        checkpoint key (``thread_id == project_id``) is passed through unchanged.
        """
        return await engine.get_workflow_state(project_id, db=self._session)

    async def start_workflow_with_session(
        self,
        engine: WorkflowEngine,
        project_id: str,
        workflow_input: EditorialWorkflowStartInput,
    ) -> CarouselWorkflowState:
        """Run the engine start use case with the request session bound.

        Binding the session here keeps the engine's reviewer-assignment + phase
        sync staging through the AE-0107 owner exactly as before; the commit is
        owned by the caller via :meth:`commit`.
        """
        return await engine.start_workflow(
            project_id,
            workflow_input,
            db=self._session,
        )

    async def mark_resume_in_progress_with_session(
        self,
        engine: WorkflowEngine,
        project_id: str,
    ) -> str:
        """Flip the engine to in_progress with the request session bound.

        The engine stages the phase-status sync through the AE-0107 owner; the
        commit is owned by the caller via :meth:`commit`.
        """
        return await engine.mark_resume_in_progress(project_id, db=self._session)

    # --- Write side: editorial intents -> AE-0107 owner -----------------------
    async def assign_reviewer(self, project_id: str, reviewer_id: str) -> None:
        """Stamp the WO ``assigned_reviewer_id`` via the single write owner."""
        await self._write_owner.assign_reviewer(project_id, reviewer_id)

    async def sync_workflow(
        self,
        project_id: str,
        state: CarouselWorkflowState,
    ) -> None:
        """Sync the WO phase/workflow columns from LangGraph state via the owner.

        Delegates to the owner's byte-identical ``sync_phase``; the ACL never
        mutates ``current_phase`` / ``phase_status`` / ``workflow_status`` (or the
        synced distribution copy) on the row itself.
        """
        await self._write_owner.sync_phase(project_id, state)

    async def set_phase_status_and_commit(
        self,
        project_id: str,
        phase_status: str,
    ) -> None:
        """Set the WO ``phase_status`` (background-runner path) via the owner."""
        await self._write_owner.set_phase_status_and_commit(project_id, phase_status)

    async def bump_resume_lock_version(
        self,
        project_id: str,
        expected_version: int | None,
    ) -> int:
        """Run the resume ``lock_version`` CAS via the single write owner.

        Delegates UNCHANGED to the owner's ``bump_resume_lock_version`` (which
        delegates to the byte-identical ``OptimisticLockService`` resume CAS), so
        the optimistic-lock expected-version contract and its pairing with the
        artifact-activation CAS are preserved exactly — the ACL adds no bump.
        """
        return await self._write_owner.bump_resume_lock_version(
            project_id,
            expected_version,
        )

    async def commit(self) -> None:
        """Commit the WO writes staged through the single write owner (UoW)."""
        await self._write_owner.commit()


__all__ = [
    "EditorialProjectView",
    "LegacyCarouselAcl",
]
