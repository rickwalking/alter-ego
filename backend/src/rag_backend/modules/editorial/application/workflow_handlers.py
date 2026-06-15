"""Command/query handlers for the editorial carousel workflow (AE-0110).

Private to the module — the public facade re-exports the handler class and its
typed command/query objects; cross-module code never imports this path directly.
These handlers are the use-case entry points the thin
``/api/carousels/{project_id}/workflow/*`` route adapters delegate to: each
orchestrates the workflow engine (start/state/resume/stream) over the
:class:`LegacyCarouselAcl` read/commit seam and returns plain data the route maps
to the HTTP/SSE response.

Behavior-preserving (AE-0110). Every handler reproduces the legacy route's data
operations EXACTLY (same engine calls, same post-commit reload, same artifact
fields, same SSE event order/framing). HTTP concerns — status codes, access
checks (``carousel_access``), sanitization, the optimistic-lock 409/400 mapping,
the SSE ``id:``/``event:``/``data:`` framing + keep-alive — stay in the route
adapter / the existing route-support validators, mirroring how the conversation
handlers keep access checks at the edge.

The handlers WRAP the existing editorial workflow engine (the
``EditorialWorkflowService`` built at the route edge via the monkeypatch-friendly
``build_editorial_workflow_service`` seam); they never reconstruct or replace it,
so the LangGraph checkpoint identifiers (``thread_id == project_id``), the
``CarouselWorkflowState`` schema, and the interrupt payloads are unchanged. The
engine is injected per call via the :class:`WorkflowEngine` protocol so this
application module imports no carousel ORM and no concrete Postgres repository —
only the editorial ACL (whose infrastructure layer owns the single ORM seam) and
the platform Unit of Work. Writes commit through the AE-0107 write owner via the
ACL; these handlers never call ``db.commit()`` directly.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

from rag_backend.application.services.carousel.editorial_workflow_types import (
    EditorialWorkflowStartInput,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.modules.editorial.infrastructure.legacy_carousel_acl import (
    LegacyCarouselAcl,
)


class WorkflowEngine(Protocol):
    """Structural contract for the wrapped editorial workflow engine.

    Matches the methods the legacy routes call on the
    ``EditorialWorkflowService`` (built at the route edge via the
    monkeypatch-friendly ``build_editorial_workflow_service`` seam). Declaring it
    as a :class:`~typing.Protocol` lets the handlers wrap the engine without
    importing the concrete service (which transitively reaches the carousel ORM),
    keeping this application module free of persistence imports.
    """

    async def get_workflow_state(
        self,
        project_id: str,
        db: object | None = ...,
    ) -> CarouselWorkflowState | None:
        """Return the persisted workflow state, or ``None`` when absent."""
        ...

    async def start_workflow(
        self,
        project_id: str,
        workflow_input: EditorialWorkflowStartInput,
        db: object | None = ...,
    ) -> CarouselWorkflowState:
        """Run synthesis/outline/draft then pause at the first human gate."""
        ...

    async def mark_resume_in_progress(
        self,
        project_id: str,
        db: object | None = ...,
    ) -> str:
        """Flip the workflow to in_progress and return the current phase."""
        ...

    def stream_phase_updates(
        self,
        project_id: str,
        *,
        phase_progress: dict[str, object] | None = ...,
    ) -> AsyncIterator[dict[str, object]]:
        """Yield workflow phase/progress events for SSE consumers."""
        ...


@dataclass(frozen=True)
class WorkflowStateView:
    """Workflow state plus the row metadata the state response needs.

    Bundles the engine ``state`` with the ``phase_progress`` / ``lock_version``
    the route's response mapper overlays, all read through the ACL so the route
    never touches the carousel ORM.
    """

    state: CarouselWorkflowState
    phase_progress: dict[str, object] | None
    lock_version: int


@dataclass(frozen=True)
class StartWorkflowCommand:
    """Inputs for the workflow-start use case (sanitized at the route edge)."""

    project_id: str
    workflow_input: EditorialWorkflowStartInput


class EditorialWorkflowHandlers:
    """Use-case handlers wrapping the workflow engine + the carousel ACL.

    Constructed per request by the inbound edge from the bootstrapped editorial
    module (the :class:`LegacyCarouselAcl`). Holds no framework state and
    resolves no global container; the workflow engine is passed in per call (the
    route resolves it through the ``build_editorial_workflow_service`` seam so the
    deterministic safety-net stub still overrides it).
    """

    def __init__(self, acl: LegacyCarouselAcl) -> None:
        self._acl = acl

    async def get_state(
        self,
        engine: WorkflowEngine,
        project_id: str,
    ) -> WorkflowStateView | None:
        """Load workflow state + row metadata, or ``None`` when no checkpoint.

        Byte-identical to the legacy GET ``workflow/state``: the engine read is
        passed the session (via the ACL) so the DB-says-in_progress merge is
        preserved, and the ``phase_progress`` / ``lock_version`` overlay is read
        from the same row through the ACL.
        """
        state = await self._acl.get_workflow_state_with_session(engine, project_id)
        if state is None:
            return None
        view = await self._acl.load_editorial(project_id)
        return WorkflowStateView(
            state=state,
            phase_progress=_phase_progress_of(view),
            lock_version=_lock_version_of(view),
        )

    async def start(
        self,
        engine: WorkflowEngine,
        command: StartWorkflowCommand,
    ) -> WorkflowStateView:
        """Run the workflow start then commit + reload through the single owner.

        Byte-identical to the legacy POST ``workflow/start``: the engine runs the
        synthesis/outline/draft phases (with the session bound via the ACL so the
        reviewer-assignment + phase sync stage through the AE-0107 owner), the WO
        writes are committed ONCE via the ACL (the platform UoW single committer),
        then the row is re-read through the ACL for the post-commit
        ``phase_progress`` / ``lock_version`` overlay. ``ValueError`` from the
        engine propagates so the route maps the existing 400.
        """
        state = await self._acl.start_workflow_with_session(
            engine,
            command.project_id,
            command.workflow_input,
        )
        await self._acl.commit()
        view = await self._acl.load_editorial(command.project_id)
        return WorkflowStateView(
            state=state,
            phase_progress=_phase_progress_of(view),
            lock_version=_lock_version_of(view),
        )

    async def mark_resume_in_progress(
        self,
        engine: WorkflowEngine,
        project_id: str,
    ) -> str:
        """Flip the workflow to in_progress, commit the WO write, return phase.

        Byte-identical to the legacy POST ``workflow/resume`` pre-background step:
        the engine stages the phase-status sync (through the AE-0107 owner) and
        this handler commits it ONCE via the ACL before the route schedules the
        fire-and-forget background resume. The optimistic-lock CAS and all resume
        gates run in the route-support validators at the edge (unchanged).
        """
        current_phase = await self._acl.mark_resume_in_progress_with_session(
            engine,
            project_id,
        )
        await self._acl.commit()
        return current_phase

    @staticmethod
    def stream_phase_updates(
        engine: WorkflowEngine,
        project_id: str,
        *,
        phase_progress: dict[str, object] | None,
    ) -> AsyncIterator[dict[str, object]]:
        """Yield the workflow phase/progress events for the SSE route.

        Pure pass-through to the engine's stream (no DB writes): the route owns
        the ``id:``/``event:``/``data:`` framing + keep-alive handling so the SSE
        contract is unchanged.
        """
        return engine.stream_phase_updates(
            project_id,
            phase_progress=phase_progress,
        )


def _phase_progress_of(view: object) -> dict[str, object] | None:
    """Read the carousel ``phase_progress`` from an editorial view, ACL-only.

    Returns ``None`` when the row is gone or the value is not a dict, matching
    the legacy ``project.phase_progress if isinstance(..., dict) else None``.
    """
    from rag_backend.modules.editorial.infrastructure.legacy_carousel_acl import (
        EditorialProjectView,
    )

    if not isinstance(view, EditorialProjectView):
        return None
    raw = view.project.project.phase_progress
    return dict(raw) if isinstance(raw, dict) else None


def _lock_version_of(view: object) -> int:
    """Read the ``lock_version`` from an editorial view, defaulting to 1.

    Matches the legacy ``int(project.lock_version or 1)`` / the absent-row
    fallback of ``1``.
    """
    from rag_backend.modules.editorial.infrastructure.legacy_carousel_acl import (
        EditorialProjectView,
    )

    if not isinstance(view, EditorialProjectView):
        return 1
    return view.lock_version


__all__ = [
    "EditorialWorkflowHandlers",
    "StartWorkflowCommand",
    "WorkflowEngine",
    "WorkflowStateView",
]
