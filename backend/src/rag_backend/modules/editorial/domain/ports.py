"""Outbound ports (Protocols) for the editorial bounded context.

The editorial ports are:

* ``CarouselRepository`` — carousel project / slide / research-source /
  image-generation persistence (re-exported, object-identity shim; see below).
* ``SourceMaterialPort`` — synthesizing the workflow's research source material.
* ``ReviewerAssignmentPort`` — assigning a human reviewer to a project.
* ``ReviewDecisionPort`` — recording reviewer review decisions
  (approve / reject / revise / edit) over the workflow.
* ``OptimisticLockingPort`` — the ``lock_version`` resume compare-and-swap.
* ``ApprovalPort`` — reading/expressing the *content-approval* state
  (``workflow_status -> approved_for_publish``) — DISTINCT from public release.
* ``PublicReleasePort`` — making approved content *publicly visible*
  (``is_public`` / visibility) — DISTINCT from approval.

Per backend/CLAUDE.md, interfaces are :class:`typing.Protocol`, never ABCs, and
they are fully typed (no ``Any``). These Protocols let the editorial
APPLICATION/domain layers depend only on contracts — never on the carousel ORM
or a concrete Postgres repository; the concrete adapters live in
``rag_backend.modules.editorial.infrastructure`` and delegate to the existing
ACL / write owner / services (behavior-preserving).

**Re-export, not relocation (AE-0108 constraint) for ``CarouselRepository``.**
That Protocol is defined in the SHARED protocol file
``rag_backend.domain.protocols.repositories`` which is imported by the carousel
routes, the workflow engine, services, and the container. Physically moving the
definition would break those imports, so this phase keeps the definition where it
is and merely **re-exports** it here. The legacy import path
(``rag_backend.domain.protocols.repositories.CarouselRepository``) keeps
resolving to the IDENTICAL Protocol object, while the editorial module domain
layer also exposes it as its own port. This mirrors
``modules.conversation.domain.ports`` exactly (object-identity shim).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from rag_backend.domain.protocols.repositories import CarouselRepository
from rag_backend.modules.editorial.domain.release import (
    ApprovalState,
    PublicReleaseState,
)


@runtime_checkable
class SourceMaterialPort(Protocol):
    """Synthesize the workflow's research source material.

    Wraps the source-synthesis step the editorial workflow runs before drafting,
    so the application layer requests synthesized research findings through a
    contract instead of reaching into the orchestrator/agents directly.
    """

    async def synthesize(
        self,
        sources: list[dict[str, str]],
    ) -> object:
        """Return synthesized research findings for the given raw sources.

        The concrete return shape is the workflow engine's research-findings
        object; the application layer treats it opaquely (it only forwards it).
        """
        ...


@runtime_checkable
class ReviewerAssignmentPort(Protocol):
    """Assign a human reviewer to a carousel project (workflow-owned write).

    Backed by the AE-0107 single write owner via the ACL so the
    ``assigned_reviewer_id`` write stays byte-identical and routed through the
    one owner; the application layer never touches the carousel ORM.
    """

    async def assign_reviewer(self, project_id: str, reviewer_id: str) -> None:
        """Stamp the project's ``assigned_reviewer_id`` (commit owned elsewhere)."""
        ...


@runtime_checkable
class ReviewDecisionPort(Protocol):
    """Record a reviewer's review decision over the workflow.

    A review decision is one of approve / reject / revise / edit (the canonical
    :data:`REVIEW_ACTIONS`). Implementations delegate to the unchanged editorial
    workflow engine's resume path so the review-action behavior + status
    transitions stay byte-identical.
    """

    async def record_decision(self, decision: object) -> object:
        """Apply the review decision and return the resulting workflow state.

        ``decision`` is the engine's resume-input value object; the result is the
        post-resume workflow state. The application layer forwards both opaquely
        so this contract introduces no behavior change.
        """
        ...


@runtime_checkable
class OptimisticLockingPort(Protocol):
    """The ``lock_version`` optimistic-lock compare-and-swap (resume path).

    Delegates UNCHANGED to the AE-0107 owner's ``bump_resume_lock_version``
    (which delegates to :meth:`OptimisticLockService.bump_carousel_version`), so
    the expected-version contract and its pairing with the artifact-activation
    CAS are preserved exactly.
    """

    async def bump_resume_lock_version(
        self,
        project_id: str,
        expected_version: int | None,
    ) -> int:
        """Validate ``expected_version`` and return the bumped ``lock_version``."""
        ...


@runtime_checkable
class ApprovalPort(Protocol):
    """Read the *content-approval* state of a project.

    Approval (``workflow_status -> approved_for_publish``) is the workflow's
    statement that the content is ready to publish. It is a DISTINCT operation
    and state from public release (see :class:`PublicReleasePort`): approving
    content does NOT make it public. This port only reports approval; the
    workflow engine remains the sole writer of ``workflow_status``.
    """

    async def get_approval_state(self, project_id: str) -> ApprovalState | None:
        """Return the project's approval state, or ``None`` when absent."""
        ...


@runtime_checkable
class PublicReleasePort(Protocol):
    """Read the *public-release* (visibility) state of a project.

    Public release (``is_public`` / homepage + blog visibility) is a DISTINCT
    operation and state from approval (see :class:`ApprovalPort`). A project may
    be approved-for-publish yet not publicly released, or vice versa. This port
    reports release state; it does not change who-can-see-what (the existing
    publish routes remain the release writer).
    """

    async def get_release_state(self, project_id: str) -> PublicReleaseState | None:
        """Return the project's public-release state, or ``None`` when absent."""
        ...


__all__ = [
    "ApprovalPort",
    "CarouselRepository",
    "OptimisticLockingPort",
    "PublicReleasePort",
    "ReviewDecisionPort",
    "ReviewerAssignmentPort",
    "SourceMaterialPort",
]
