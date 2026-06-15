"""Anti-corruption layer: legacy ``carousel_projects`` presentation persistence
↔ the presentation context (AE-0118).

This module is the **single** seam between the presentation bounded context and
the legacy carousel persistence for the presentation surface. Together with
:class:`PresentationWriteOwner` it is the only place under
``rag_backend.modules.presentation`` that imports the carousel / slide ORM
(``CarouselProjectModel``); the presentation application and domain layers stay
free of it. Everything the ACL exposes upward is in presentation terms
(:class:`PresentationProject` view), and everything it writes downward goes
**through** the :class:`PresentationWriteOwner`, never by mutating an ORM row
here.

**Read side.** Translates a session-attached ``CarouselProjectModel`` into the
presentation VIEW aggregate — the canonical :class:`CarouselProject` entity (via
the model's own ``to_entity`` — no second translator) wrapped as a
:class:`PresentationProject`. The ``lock_version`` optimistic-lock token is
surfaced verbatim alongside the view so callers can read the concurrency token
without touching the ORM.

**Write side.** The presentation-owned writes — the design-token refresh, the
PDF-path writes, the slide create/update, the artifact-activation CAS, and the
resume ``lock_version`` bump — are all **delegated** to the injected
:class:`PresentationWriteOwner` (the single write owner). The ACL adds no
persistence of its own and never calls ``session.add`` / ``flush`` / ``commit``
on the carousel row, so the owner stays the sole writer and the single committer
for those fields.

**Behavior-preserving (AE-0118).** No routes are moved (AE-0120), no schema
changes, and no second persistence translator. The ``artifact_version`` ↔
``lock_version`` compound CAS and the shared-lock coordination with the editorial
AE-0107 owner are preserved exactly — the ACL never rewrites an id and never
bumps the lock outside the owner's byte-identical CAS delegations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.presentation.domain.models import (
    CarouselProject,
    CarouselSlide,
    PresentationProject,
)
from rag_backend.modules.presentation.infrastructure.presentation_write_owner import (
    PresentationWriteOwner,
)

if TYPE_CHECKING:
    from rag_backend.domain.models.carousel import DesignTokens
    from rag_backend.infrastructure.database.carousel_artifact_build_repository import (
        _ActivateBuildParams,
    )

# Default optimistic-lock token for a row whose ``lock_version`` is unset, kept
# identical to the legacy reads (``int(model.lock_version or 1)``) so the token
# the ACL surfaces matches what the activation / resume CAS expect.
_DEFAULT_LOCK_VERSION = 1


@dataclass(frozen=True)
class PresentationProjectView:
    """A presentation VIEW aggregate plus its legacy concurrency token.

    Surfaces the :class:`PresentationProject` (presentation terms only) together
    with the legacy ``lock_version`` optimistic-lock token read verbatim from the
    row. Callers read the token through this view instead of touching the carousel
    ORM, keeping the ACL/owner the only presentation carousel-persistence
    importers.
    """

    presentation: PresentationProject
    lock_version: int

    @property
    def project(self) -> CarouselProject:
        """The canonical carousel project entity the view wraps."""
        return self.presentation.project


class PresentationPersistenceAcl:
    """Translate legacy carousel persistence to/from presentation concepts.

    The ACL binds the request-scoped session (for reads) and the
    :class:`PresentationWriteOwner` (for all presentation writes). It performs no
    persistence of its own: reads go through the ORM model's existing
    ``to_entity`` translator, and every write is delegated to the owner so the
    owner stays the single writer + single committer for the presentation
    columns and slide rows.
    """

    def __init__(
        self,
        session: AsyncSession,
        write_owner: PresentationWriteOwner,
    ) -> None:
        self._session = session
        self._write_owner = write_owner

    # --- Read side: legacy row -> presentation view ---------------------------
    @staticmethod
    def to_presentation(model: CarouselProjectModel) -> PresentationProjectView:
        """Map a legacy ``CarouselProjectModel`` to the presentation VIEW.

        Reuses the model's canonical ``to_entity`` (no second translator) for the
        :class:`CarouselProject`, wraps it as a :class:`PresentationProject`, and
        surfaces the ``lock_version`` token verbatim.
        """
        project = model.to_entity()
        return PresentationProjectView(
            presentation=PresentationProject(project=project),
            lock_version=int(model.lock_version or _DEFAULT_LOCK_VERSION),
        )

    async def load_presentation(
        self,
        project_id: str,
    ) -> PresentationProjectView | None:
        """Load the presentation VIEW for a project, or ``None`` if absent."""
        model = await self._session.get(CarouselProjectModel, project_id)
        if model is None:
            return None
        return self.to_presentation(model)

    async def load_assigned_reviewer_id(
        self,
        project_id: str,
    ) -> str | None:
        """Read the row's ``assigned_reviewer_id`` for the preview access check.

        The preview routes admit the assigned reviewer in addition to the
        owner/admin; the id is read here (the single ORM seam) so the thin route
        adapter never touches the carousel model. Byte-identical to the legacy
        preview ``_assigned_reviewer_id`` read (``None`` when the row is absent).
        """
        model = await self._session.get(CarouselProjectModel, project_id)
        if model is None:
            return None
        return model.assigned_reviewer_id

    # --- Write side: presentation intents -> single write owner ---------------
    async def refresh_design_tokens(
        self,
        project: CarouselProject,
        design_tokens: DesignTokens,
    ) -> None:
        """Refresh ``design_tokens`` via the single write owner (flush only)."""
        await self._write_owner.set_design_tokens(project, design_tokens)

    async def update_project(self, project: CarouselProject) -> None:
        """Persist the presentation columns via the single write owner."""
        await self._write_owner.update_project(project)

    async def create_slide(self, slide: CarouselSlide) -> None:
        """Create a slide row via the single write owner (flush only)."""
        await self._write_owner.create_slide(slide)

    async def update_slide(self, slide: CarouselSlide) -> None:
        """Update a slide row via the single write owner (flush only)."""
        await self._write_owner.update_slide(slide)

    async def activate_artifact(self, params: _ActivateBuildParams) -> int:
        """Run the artifact-activation compound CAS via the owner (unchanged)."""
        return await self._write_owner.activate_artifact(params)

    async def bump_resume_lock_version(
        self,
        project_id: str,
        expected_version: int | None,
    ) -> int:
        """Run the resume ``lock_version`` CAS via the owner (shared primitive)."""
        return await self._write_owner.bump_resume_lock_version(
            project_id,
            expected_version,
        )

    async def commit(self) -> None:
        """Commit the presentation writes staged through the owner (UoW)."""
        await self._write_owner.commit()


__all__ = [
    "PresentationPersistenceAcl",
    "PresentationProjectView",
]
