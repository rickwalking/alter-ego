"""Application service (use case) for the editorial bounded context.

Private to the module. The public facade re-exports this type under its public
name; cross-module code never imports this path directly.

The service wires to the editorial **ports** (Protocols in
``rag_backend.modules.editorial.domain.ports``) via manual constructor injection
(ADR-0009 §9). It depends ONLY on those contracts — never on the carousel ORM or
a concrete Postgres repository — so the persistence/engine details stay behind
the adapters built at the inbound edge (AE-0111).

It exposes:

* ``get_project`` — the editorial aggregate read (scaffolding; AE-0108);
* ``synthesize_sources`` — source-material synthesis (``SourceMaterialPort``);
* ``assign_reviewer`` — reviewer assignment (``ReviewerAssignmentPort``);
* ``record_review_decision`` — a reviewer decision (``ReviewDecisionPort``);
* ``bump_resume_lock_version`` — the resume ``lock_version`` CAS
  (``OptimisticLockingPort``);
* ``get_approval_state`` / ``get_release_state`` — the AE-0111 contract split
  (approval ``!=`` public release), each a DISTINCT read.

Behavior-preserving: every method forwards to an injected port, whose adapter
delegates to the unchanged infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from rag_backend.modules.editorial.domain.models import EditorialProject
from rag_backend.modules.editorial.domain.ports import (
    ApprovalPort,
    CarouselRepository,
    OptimisticLockingPort,
    PublicReleasePort,
    ReviewDecisionPort,
    ReviewerAssignmentPort,
    SourceMaterialPort,
)
from rag_backend.modules.editorial.domain.release import (
    ApprovalState,
    PublicReleaseState,
)


@dataclass(frozen=True)
class EditorialPorts:
    """Optional editorial ports the service forwards to (AE-0111).

    Grouped into one typed bundle so the service keeps to a single grouped
    argument beyond the repository (backend/CLAUDE.md ≤3 args). Each port is
    optional so the AE-0108 scaffolding (repository-only) keeps working; a method
    whose port is absent raises a clear :class:`RuntimeError` rather than
    silently no-op'ing.
    """

    source_material: SourceMaterialPort | None = None
    reviewer_assignment: ReviewerAssignmentPort | None = None
    review_decision: ReviewDecisionPort | None = None
    optimistic_locking: OptimisticLockingPort | None = None
    approval: ApprovalPort | None = None
    public_release: PublicReleasePort | None = None


class EditorialService:
    """Coordinates editorial use cases over the editorial ports.

    Dependencies are injected through the constructor (manual constructor
    injection, ADR-0009 §9). The single transaction owner (Unit of Work) is
    supplied to the inbound edge via the module's bootstrap; the write use cases
    here forward to ports whose adapters stage through that owner.
    """

    def __init__(
        self,
        repository: CarouselRepository,
        ports: EditorialPorts | None = None,
    ) -> None:
        self._repository = repository
        self._ports = ports or EditorialPorts()

    async def get_project(self, project_id: UUID) -> EditorialProject | None:
        """Return the editorial aggregate for a project, or ``None`` if absent."""
        project = await self._repository.get_project_by_id(project_id)
        if project is None:
            return None
        return EditorialProject(project=project)

    async def synthesize_sources(self, sources: list[dict[str, str]]) -> object:
        """Synthesize the workflow's source material via the source port."""
        return await self._require_source_material().synthesize(sources)

    async def assign_reviewer(self, project_id: str, reviewer_id: str) -> None:
        """Assign a reviewer via the reviewer-assignment port."""
        await self._require_reviewer_assignment().assign_reviewer(
            project_id,
            reviewer_id,
        )

    async def record_review_decision(self, decision: object) -> object:
        """Record a reviewer decision via the review-decision port."""
        return await self._require_review_decision().record_decision(decision)

    async def bump_resume_lock_version(
        self,
        project_id: str,
        expected_version: int | None,
    ) -> int:
        """Run the resume ``lock_version`` CAS via the optimistic-locking port."""
        return await self._require_optimistic_locking().bump_resume_lock_version(
            project_id,
            expected_version,
        )

    async def get_approval_state(self, project_id: str) -> ApprovalState | None:
        """Return the *content-approval* state — DISTINCT from public release."""
        return await self._require_approval().get_approval_state(project_id)

    async def get_release_state(self, project_id: str) -> PublicReleaseState | None:
        """Return the *public-release* state — DISTINCT from approval."""
        return await self._require_public_release().get_release_state(project_id)

    def _require_source_material(self) -> SourceMaterialPort:
        port = self._ports.source_material
        if port is None:
            raise RuntimeError(_ERR_NO_PORT.format(name="source_material"))
        return port

    def _require_reviewer_assignment(self) -> ReviewerAssignmentPort:
        port = self._ports.reviewer_assignment
        if port is None:
            raise RuntimeError(_ERR_NO_PORT.format(name="reviewer_assignment"))
        return port

    def _require_review_decision(self) -> ReviewDecisionPort:
        port = self._ports.review_decision
        if port is None:
            raise RuntimeError(_ERR_NO_PORT.format(name="review_decision"))
        return port

    def _require_optimistic_locking(self) -> OptimisticLockingPort:
        port = self._ports.optimistic_locking
        if port is None:
            raise RuntimeError(_ERR_NO_PORT.format(name="optimistic_locking"))
        return port

    def _require_approval(self) -> ApprovalPort:
        port = self._ports.approval
        if port is None:
            raise RuntimeError(_ERR_NO_PORT.format(name="approval"))
        return port

    def _require_public_release(self) -> PublicReleasePort:
        port = self._ports.public_release
        if port is None:
            raise RuntimeError(_ERR_NO_PORT.format(name="public_release"))
        return port


# Message template for a use case invoked without its required port wired.
_ERR_NO_PORT = "editorial port not wired: {name}"


__all__ = [
    "EditorialPorts",
    "EditorialService",
]
