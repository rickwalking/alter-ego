"""Concrete adapters for the editorial outbound ports (AE-0111).

These adapters are the infrastructure backing for the editorial domain ports
(``rag_backend.modules.editorial.domain.ports``). They keep the editorial
APPLICATION/domain layers free of the carousel ORM and the concrete Postgres
repository: every port the application depends on is satisfied here by
**delegating** to the existing, unchanged infrastructure —

* the AE-0107 single write owner via the AE-0109 :class:`LegacyCarouselAcl`
  (reviewer assignment, the ``lock_version`` resume CAS, and the read of the
  approval / public-release state), and
* the wrapped editorial workflow engine (source-material synthesis and review
  decisions), injected via the :class:`WorkflowEngine` /
  :class:`ReviewWorkflowEngine` structural protocols so this module imports no
  concrete service (which transitively reaches the ORM).

Behavior-preserving: no adapter mutates an ORM row, bumps a lock, or changes a
status itself — each forwards to the byte-identical existing path, so the
``lock_version`` semantics, the review-action behavior, and the status
transitions are untouched. The approval-vs-release split is expressed purely as
two READ adapters over the SAME row (``workflow_status`` vs. ``is_public``); it
changes no visibility behavior.
"""

from __future__ import annotations

from typing import Protocol

from rag_backend.application.services.carousel.editorial_workflow_types import (
    ResumeWorkflowInput,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.modules.editorial.domain.release import (
    ApprovalState,
    PublicReleaseState,
)
from rag_backend.modules.editorial.infrastructure.legacy_carousel_acl import (
    LegacyCarouselAcl,
)


class SourceSynthesisEngine(Protocol):
    """Structural contract for the engine's source-material synthesis step."""

    async def synthesize_research(
        self,
        sources: list[dict[str, str]],
    ) -> object:
        """Return synthesized research findings for the given raw sources."""
        ...


class ReviewWorkflowEngine(Protocol):
    """Structural contract for the engine's review-decision (resume) step."""

    async def resume_workflow(
        self,
        params: ResumeWorkflowInput,
    ) -> CarouselWorkflowState:
        """Resume the workflow for a reviewer decision; return the new state."""
        ...


class EngineSourceMaterialAdapter:
    """:class:`SourceMaterialPort` backed by the workflow engine.

    Forwards source synthesis to the engine's unchanged
    ``synthesize_research`` so the research findings are produced exactly as
    before; the application layer depends only on the port.
    """

    def __init__(self, engine: SourceSynthesisEngine) -> None:
        self._engine = engine

    async def synthesize(self, sources: list[dict[str, str]]) -> object:
        """Delegate to the engine's byte-identical research synthesis."""
        return await self._engine.synthesize_research(sources)


class EngineReviewDecisionAdapter:
    """:class:`ReviewDecisionPort` backed by the workflow engine.

    Forwards a reviewer decision to the engine's unchanged ``resume_workflow``,
    preserving the approve/reject/revise/edit behavior, the revision-cap gates,
    and every status transition exactly.
    """

    def __init__(self, engine: ReviewWorkflowEngine) -> None:
        self._engine = engine

    async def record_decision(self, decision: object) -> object:
        """Apply the decision via the engine resume path; return the new state.

        ``decision`` must be a :class:`ResumeWorkflowInput`; mistyped input is a
        programming error and surfaces as a ``TypeError`` rather than silently
        changing behavior.
        """
        if not isinstance(decision, ResumeWorkflowInput):
            raise TypeError(_ERR_DECISION_TYPE)
        return await self._engine.resume_workflow(decision)


class AclReviewerAssignmentAdapter:
    """:class:`ReviewerAssignmentPort` backed by the carousel ACL / write owner.

    Forwards the ``assigned_reviewer_id`` stamp to the ACL (which delegates to the
    AE-0107 single write owner); the commit boundary stays with the caller.
    """

    def __init__(self, acl: LegacyCarouselAcl) -> None:
        self._acl = acl

    async def assign_reviewer(self, project_id: str, reviewer_id: str) -> None:
        """Stamp the reviewer via the ACL → single write owner (flush only)."""
        await self._acl.assign_reviewer(project_id, reviewer_id)


class AclOptimisticLockingAdapter:
    """:class:`OptimisticLockingPort` backed by the carousel ACL / write owner.

    Forwards the resume ``lock_version`` compare-and-swap UNCHANGED to the ACL
    (→ owner → :meth:`OptimisticLockService.bump_carousel_version`), so the
    expected-version contract and the artifact-activation CAS pairing are
    preserved exactly.
    """

    def __init__(self, acl: LegacyCarouselAcl) -> None:
        self._acl = acl

    async def bump_resume_lock_version(
        self,
        project_id: str,
        expected_version: int | None,
    ) -> int:
        """Run the resume CAS via the ACL → single write owner."""
        return await self._acl.bump_resume_lock_version(project_id, expected_version)


class AclApprovalAdapter:
    """:class:`ApprovalPort` backed by the carousel ACL (read-only).

    Reads the project's *content-approval* state from ``workflow_status`` through
    the ACL — DISTINCT from public release. This adapter never writes; the
    workflow engine remains the sole writer of ``workflow_status``.
    """

    def __init__(self, acl: LegacyCarouselAcl) -> None:
        self._acl = acl

    async def get_approval_state(self, project_id: str) -> ApprovalState | None:
        """Return the approval state read via the ACL, or ``None`` if absent."""
        view = await self._acl.load_editorial(project_id)
        if view is None:
            return None
        return ApprovalState.from_workflow_status(view.project.workflow.workflow_status)


class AclPublicReleaseAdapter:
    """:class:`PublicReleasePort` backed by the carousel ACL (read-only).

    Reads the project's *public-release* (visibility) state from ``is_public``
    through the ACL — DISTINCT from approval. This adapter never writes; the
    existing publish routes remain the sole writer of ``is_public``.
    """

    def __init__(self, acl: LegacyCarouselAcl) -> None:
        self._acl = acl

    async def get_release_state(self, project_id: str) -> PublicReleaseState | None:
        """Return the release state read via the ACL, or ``None`` if absent."""
        view = await self._acl.load_editorial(project_id)
        if view is None:
            return None
        return PublicReleaseState.from_is_public(
            is_public=view.project.project.is_public,
        )


# Programming-error message for a mistyped review decision.
_ERR_DECISION_TYPE = "review decision must be a ResumeWorkflowInput"


__all__ = [
    "AclApprovalAdapter",
    "AclOptimisticLockingAdapter",
    "AclPublicReleaseAdapter",
    "AclReviewerAssignmentAdapter",
    "EngineReviewDecisionAdapter",
    "EngineSourceMaterialAdapter",
    "ReviewWorkflowEngine",
    "SourceSynthesisEngine",
]
