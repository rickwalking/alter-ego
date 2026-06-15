"""Single write owner for the presentation ``carousel_projects`` columns + slide
rows (AE-0118).

Per the AE-0115 presentation surface-ownership map (§2 columns, §7 slide columns,
§4 multi-writer set) every *presentation-owned* (PO) column of the legacy
``carousel_projects`` row and every ``CarouselSlideModel`` row has exactly one
write owner. This module is that owner — the presentation single-writer adapter.
It is the **only** file under ``rag_backend.modules.presentation`` that imports
the carousel / slide ORM (``CarouselProjectModel`` / ``CarouselSlideModel``); the
presentation application and domain layers stay free of it. Everything it exposes
upward is reached through the presentation public facade.

**What it owns.**

* The presentation project columns — ``design_tokens``, ``output_dir``,
  ``pdf_path`` / ``pdf_path_en``, ``slide_layout_strategy``,
  ``presentation_policy_version`` / ``presentation_policy_checksum``, the
  title/subtitle (PT + EN), the brand colors, and the creator-watermark metadata
  (``creator_*``) — written by re-stamping the row from the canonical
  :class:`CarouselProject` entity via the model's own ``update_from_entity`` (no
  second translator).
* The slide rows — created / updated from the canonical :class:`CarouselSlide`
  entity via the slide model's ``from_entity`` / ``update_from_entity``.
* The artifact-activation compare-and-swap (``artifact_version`` ↔
  ``lock_version``) — **delegated UNCHANGED** to
  :meth:`PostgresCarouselArtifactBuildRepository.activate_build`, the persisting
  compound CAS (§3).
* The resume ``lock_version`` bump — **delegated UNCHANGED** to
  :meth:`OptimisticLockService.bump_carousel_version`, the SAME shared CAS
  primitive the editorial AE-0107 owner uses (§3.1).

**Shared-owner coordination (§3.1).** ``lock_version`` is the single
optimistic-lock token guarding BOTH the editorial resume bump and the
presentation activation bump. This owner does not treat it as private: the
activation bump goes through the compound CAS
``WHERE lock_version=source AND artifact_version=prior`` (bumping both atomically)
and the resume bump goes through the row-level CAS ``WHERE lock_version=current``.
Both are the *same* DB-level compare-and-swap primitive on the one column, so an
activation and a concurrent resume cannot interleave-clobber: each validates its
expected/source version, and the loser gets its conflict
(``ERR_ARTIFACT_BUILD_CONFLICT`` / ``ERR_VERSION_CONFLICT``) — never a silent
overwrite. The pairing stays atomic and ``lock_version`` advances by exactly one
per successful bump. This owner changes NO lock semantics.

**Commit boundary.** Mutation helpers only ``flush`` (staging the row changes
inside the open transaction); the owner is the single committer for those writes
via the platform :class:`SqlAlchemyUnitOfWork` (ADR-0009 §9). Callers that
previously called ``session.commit()`` for the presentation columns now call
:meth:`commit`. The activation CAS keeps its own commit boundary inside
``CarouselArtifactBuildService`` (unchanged), so this owner does not double-commit
it.

**Behavior-preserving (AE-0118).** The column / slide values written here are
byte-identical to the pre-AE-0118 scattered writers (admin design-token refresh,
the artifact build PDF-path writes, the generic slide writes); only the
*ownership* and the *commit boundary* are consolidated. No routes are moved
(AE-0120), no schema changes, no second persistence translator.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.optimistic_lock_service import (
    CarouselVersionBumpParams,
    OptimisticLockService,
)
from rag_backend.domain.models import CarouselProject, CarouselSlide
from rag_backend.infrastructure.database.carousel_artifact_build_repository import (
    PostgresCarouselArtifactBuildRepository,
    _ActivateBuildParams,
)
from rag_backend.infrastructure.database.models.carousel import (
    CarouselProjectModel,
    CarouselSlideModel,
)
from rag_backend.platform.database import SqlAlchemyUnitOfWork

if TYPE_CHECKING:
    from rag_backend.domain.models.carousel import DesignTokens

# Error raised when a presentation write targets an absent project/slide row.
# Mirrors the generic repository's not-found contract so the behavior (and the
# admin refresh per-project error capture) stays byte-identical.
_ERR_PROJECT_NOT_FOUND = "Carousel project {} not found"
_ERR_SLIDE_NOT_FOUND = "Carousel slide {} not found"


class PresentationWriteOwner:
    """Sole writer of the presentation ``carousel_projects`` columns + slide rows.

    Wraps the request-scoped session via the platform Unit of Work so the owner
    is also the single committer for the presentation writes it stages. Mutation
    helpers only ``flush``; callers commit through :meth:`commit` (the UoW). The
    artifact-activation and resume-lock compare-and-swaps are delegated UNCHANGED
    to their existing shared primitives (the compound activation CAS and the
    optimistic-lock service), preserving the ``artifact_version`` ↔
    ``lock_version`` pairing exactly.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._uow = SqlAlchemyUnitOfWork(session)
        self._build_repo = PostgresCarouselArtifactBuildRepository(session)

    async def commit(self) -> None:
        """Commit the presentation writes staged in the request (UoW)."""
        await self._uow.commit()

    # --- Project-column writes (re-stamp the row from the entity; flush only) ---
    async def update_project(self, project: CarouselProject) -> None:
        """Persist the presentation columns from the canonical entity (flush only).

        Re-stamps the row via the model's own ``update_from_entity`` (no second
        translator), exactly as the generic ``CarouselRepository.update_project``
        does, but WITHOUT committing — the owner owns the commit boundary so the
        scattered ``session.commit()`` callers route through :meth:`commit`.
        Returns ``None`` (flush only): the caller re-reads through the ACL if it
        needs the refreshed entity, avoiding a post-flush lazy reload of the
        server-managed ``updated_at`` column.
        """
        model = await self._session.get(CarouselProjectModel, str(project.id))
        if model is None:
            raise ValueError(_ERR_PROJECT_NOT_FOUND.format(project.id))
        model.update_from_entity(project)
        await self._session.flush()

    async def set_design_tokens(
        self,
        project: CarouselProject,
        design_tokens: DesignTokens,
    ) -> None:
        """Refresh the project's ``design_tokens`` via the owner (flush only).

        Stamps ``design_tokens`` on the canonical entity and re-stamps the row
        through :meth:`update_project`, byte-identical to the legacy admin
        refresh (which set ``project.design_tokens`` then ``update_project``);
        only the commit moves to the owner's :meth:`commit`.
        """
        project.design_tokens = design_tokens
        await self.update_project(project)

    # --- Slide-row writes (canonical entity ↔ model; flush only) ---------------
    async def create_slide(self, slide: CarouselSlide) -> None:
        """Create a slide row from the canonical entity (flush only)."""
        model = CarouselSlideModel.from_entity(slide)
        self._session.add(model)
        await self._session.flush()

    async def update_slide(self, slide: CarouselSlide) -> None:
        """Update a slide row from the canonical entity (flush only)."""
        model = await self._session.get(CarouselSlideModel, str(slide.id))
        if model is None:
            raise ValueError(_ERR_SLIDE_NOT_FOUND.format(slide.id))
        model.update_from_entity(slide)
        await self._session.flush()

    # --- Compare-and-swap paths (shared lock_version token; delegated) ---------
    async def activate_artifact(
        self,
        params: _ActivateBuildParams,
    ) -> int:
        """Run the artifact-activation compound CAS UNCHANGED; return new lock.

        Delegates to :meth:`PostgresCarouselArtifactBuildRepository.activate_build`
        — the persisting compound CAS whose guard is
        ``(lock_version == source AND artifact_version == prior)`` and which bumps
        BOTH ``artifact_version`` and ``lock_version`` atomically (§3). The
        pairing is preserved byte-identical: the owner adds no extra bump and
        does not commit here (the build service owns that commit), so the shared
        ``lock_version`` token stays governed by the one CAS primitive.
        """
        return await self._build_repo.activate_build(params=params)

    async def bump_resume_lock_version(
        self,
        project_id: str,
        expected_version: int | None,
    ) -> int:
        """Run the resume ``lock_version`` CAS via the SHARED primitive (flush only).

        Delegates UNCHANGED to ``OptimisticLockService.bump_carousel_version`` —
        the SAME shared CAS primitive the editorial AE-0107 owner uses (§3.1) —
        so the two owners coordinate on the one ``lock_version`` token: a resume
        bump invalidates a stale ``source_lock_version`` held by an in-flight
        activation (and vice-versa), and the loser gets ``ERR_VERSION_CONFLICT``
        rather than a silent overwrite. The commit is owned by the caller via
        :meth:`commit`.
        """
        return await OptimisticLockService().bump_carousel_version(
            self._session,
            CarouselVersionBumpParams(
                project_id=project_id,
                expected_version=expected_version,
            ),
        )


__all__ = ["PresentationWriteOwner"]
