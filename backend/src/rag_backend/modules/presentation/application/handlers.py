"""Command/query handlers for the carousel presentation surface (AE-0120).

Private to the module — the public facade re-exports the handler class and its
typed command/query objects; cross-module code never imports this path directly.
These handlers are the use-case entry points the thin presentation route adapters
(``media`` / ``preview`` / ``strategies`` / ``admin`` / ``creator-asset`` and the
``crud`` project-GET design-token merge) delegate to: each reads/writes the
presentation surface through the AE-0118 :class:`PresentationPersistenceAcl`
seam (the single ORM importer, alongside its owner) and returns plain data the
route maps to the HTTP response / FileResponse.

Behavior-preserving (AE-0120). Every handler reproduces the legacy route's data
operations EXACTLY: the same project/slide reads, the same design-token merge,
the same strategy re-render, the same admin bulk loops, and the same
creator-asset upload/select calls. HTTP concerns — status codes, access checks
(``resource_access`` / creator-asset / owner-admin), the FileResponse
content-type/headers/bytes, the response-schema construction, and the artifact
URL strings — stay in the route adapter, mirroring how the editorial workflow
handlers keep access checks + SSE framing at the edge.

The handlers WRAP the existing collaborators: the ACL (read/write seam over the
AE-0118 single write owner), the carousel-refinement service (strategy
re-render), and the creator-asset application service. They never reconstruct or
replace them. This application module imports NO carousel/slide ORM and NO
concrete Postgres repository — only the module's own ACL (whose infrastructure
layer owns the single ORM seam) and application-layer services/value objects.
Writes commit through the AE-0118 write owner via the ACL; these handlers never
call ``db.commit()`` directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from uuid import UUID

from rag_backend.application.services.carousel.creator_asset_service import (
    CreatorAssetSelectCommand,
    CreatorAssetService,
    CreatorAssetUploadCommand,
)
from rag_backend.application.services.carousel.design_token_utils import (
    merge_design_tokens_with_disk,
)
from rag_backend.application.services.carousel.strategy_handlers import (
    StrategyInfo,
    StrategyListResponse,
)
from rag_backend.application.services.carousel_template.design import (
    generate_design_tokens,
)
from rag_backend.application.services.carousel_template.strategies.registry import (
    SlideLayoutRegistry,
)
from rag_backend.domain.models import (
    CarouselCreatorAsset,
    CarouselProject,
    CarouselSlide,
    CarouselStatus,
)
from rag_backend.domain.protocols import CarouselRefinementService, CarouselRepository
from rag_backend.domain.protocols.repositories import _ProjectQuery
from rag_backend.modules.presentation.infrastructure.presentation_acl import (
    PresentationPersistenceAcl,
)

# Status filter + paging for the admin bulk loops — byte-identical to the legacy
# admin routes (``status=COMPLETED, limit=1000, offset=0``).
_ADMIN_PROJECT_STATUS = CarouselStatus.COMPLETED
_ADMIN_PROJECT_LIMIT = 1000
_ADMIN_PROJECT_OFFSET = 0


@runtime_checkable
class SlideMissingPredicate(Protocol):
    """Probe for whether a project's rendered slides are missing.

    The admin ``render-slides`` skip check (the legacy ``_slide_missing`` on-disk
    probe) is supplied by the route — it owns the rendering/disk details — so the
    handler stays free of them while keeping the skip behavior byte-identical. The
    predicate is a callable invoked per project inside the bulk loop.
    """

    def __call__(self, project: CarouselProject) -> bool:
        """Return whether the project is missing rendered slides."""
        ...


@dataclass(frozen=True)
class PresentationBulkResult:
    """Per-project bulk outcome for the admin refresh / render loops.

    Carries the same counters the admin routes return (``updated`` / ``skipped``
    / ``failed`` / ``errors``); the route maps it to its response model. ``total``
    is derived by the route from the project count it requests so the response is
    byte-identical.
    """

    updated: int
    skipped: int
    failed: int
    errors: list[str]


@dataclass(frozen=True)
class CreatorAssetResult:
    """The created/selected creator asset plus the updated project.

    Mirrors the ``(asset, project)`` tuple the creator-asset service returns; the
    route maps the asset to its response model (the project is the staged side
    effect, kept so the contract is unchanged).
    """

    asset: CarouselCreatorAsset
    project: CarouselProject


class PresentationHandlers:
    """Use-case handlers wrapping the presentation ACL + collaborators.

    Constructed per request by the inbound edge from the bootstrapped
    presentation module. Holds the AE-0118 :class:`PresentationPersistenceAcl`
    (the single read/write seam over the presentation columns + slide rows) and
    the request-scoped collaborators (the generic carousel repository — used only
    for the read queries the legacy presentation routes issued — the refinement
    service, the strategy registry, and the creator-asset service). Resolves no
    global container; everything is injected via the constructor (ADR-0009 §9).
    """

    def __init__(
        self,
        acl: PresentationPersistenceAcl,
        collaborators: PresentationCollaborators,
    ) -> None:
        self._acl = acl
        self._repository = collaborators.repository
        self._refinement = collaborators.refinement
        self._registry = collaborators.registry
        self._creator_assets = collaborators.creator_assets

    # --- Read side: project / slide reads (presentation responses) -------------
    async def get_project(self, project_id: UUID) -> CarouselProject | None:
        """Load the carousel project for a presentation response, or ``None``.

        Byte-identical to the legacy presentation routes' ``repo.get_project_by_id``
        read; the route applies the access check + builds the response/FileResponse.
        """
        return await self._repository.get_project_by_id(project_id)

    async def get_slides(self, project_id: UUID) -> list[CarouselSlide]:
        """Load the project's slides for the ``/slides`` response.

        Byte-identical to ``repo.get_slides_by_project``; the route validates the
        owner/admin access and maps each slide to its response model.
        """
        return await self._repository.get_slides_by_project(project_id)

    async def get_assigned_reviewer_id(self, project_id: UUID) -> str | None:
        """Read the project's ``assigned_reviewer_id`` for the preview access check.

        Byte-identical to the legacy preview ``_assigned_reviewer_id`` read; the
        id is fetched through the ACL (the single ORM seam) so the preview route
        adapter never touches the carousel model. Returns ``None`` when the row is
        absent.
        """
        return await self._acl.load_assigned_reviewer_id(str(project_id))

    @staticmethod
    def merge_design_tokens(project: CarouselProject) -> dict[str, object]:
        """Merge the project's DB design tokens with the on-disk slide layout.

        The presentation-owned read (AE-0115 §6): byte-identical to
        ``merge_design_tokens_with_disk(project)`` — response-only, nothing is
        persisted. Centralized here so the ``design`` / ``preview/design`` /
        ``crud`` project-GET routes reach the merge through the facade instead of
        importing the merge utility directly.
        """
        return merge_design_tokens_with_disk(project)

    # --- Strategies ------------------------------------------------------------
    def list_strategies(self) -> StrategyListResponse:
        """List the registered slide-layout strategies (registry-driven).

        Byte-identical to the legacy ``GET /strategies``: reads the registry and
        maps each entry to :class:`StrategyInfo`.
        """
        raw = self._registry.list()
        return StrategyListResponse(
            strategies=[
                StrategyInfo(name=entry["name"], display_name=entry["display_name"])
                for entry in raw
            ]
        )

    def strategy_exists(self, name: str) -> bool:
        """Whether ``name`` is a registered strategy (registry lookup).

        Mirrors the legacy route's ``registry.get(name)`` existence probe so the
        route maps the unknown-strategy 422 unchanged.
        """
        try:
            self._registry.get(name)
        except LookupError:
            return False
        return True

    async def apply_strategy(
        self,
        project_id: UUID,
        name: str,
    ) -> None:
        """Re-render the project's slides with the named strategy.

        Byte-identical to the legacy ``PUT /{project_id}/strategy`` write: the
        route validates the strategy exists, loads + status-checks the project,
        then this handler runs ``refinement.re_render_slides`` (the single write
        path — refinement owns its persistence/commit, unchanged).
        """
        await self._refinement.re_render_slides(project_id, strategy=name)

    # --- Admin bulk loops ------------------------------------------------------
    async def list_completed_projects(self) -> list[CarouselProject]:
        """Load all COMPLETED projects for the admin bulk loops.

        Byte-identical to the legacy admin routes' ``repo.get_all_projects`` with
        ``status=COMPLETED, limit=1000, offset=0``.
        """
        return await self._repository.get_all_projects(
            query=_ProjectQuery(
                status=_ADMIN_PROJECT_STATUS,
                limit=_ADMIN_PROJECT_LIMIT,
                offset=_ADMIN_PROJECT_OFFSET,
            ),
        )

    async def refresh_design_tokens(
        self,
        projects: list[CarouselProject],
    ) -> PresentationBulkResult:
        """Regenerate + persist design tokens for each project via the owner.

        Byte-identical to the legacy admin ``refresh-design-tokens``: for each
        project it stamps ``generate_design_tokens(project)`` through the AE-0118
        single write owner (flush only) capturing per-project errors, then commits
        ONCE through the ACL (the platform UoW single committer). Routes no longer
        call ``session.commit()`` directly.
        """
        updated = 0
        failed = 0
        errors: list[str] = []
        for project in projects:
            try:
                await self._acl.refresh_design_tokens(
                    project,
                    generate_design_tokens(project),
                )
                updated += 1
            except Exception as exc:
                failed += 1
                errors.append(f"{project.id}: {exc}")
        await self._acl.commit()
        return PresentationBulkResult(
            updated=updated,
            skipped=0,
            failed=failed,
            errors=errors,
        )

    async def render_slides(
        self,
        projects: list[CarouselProject],
        missing: SlideMissingPredicate,
    ) -> PresentationBulkResult:
        """Re-render slides for projects missing rendered output.

        Byte-identical to the legacy admin ``render-slides``: skips projects whose
        slides already exist (per the injected predicate), otherwise runs
        ``refinement.re_render_slides`` capturing per-project errors. Refinement
        owns its persistence/commit, unchanged.
        """
        updated = 0
        skipped = 0
        failed = 0
        errors: list[str] = []
        for project in projects:
            if not missing(project):
                skipped += 1
                continue
            try:
                await self._refinement.re_render_slides(project.id)
                updated += 1
            except Exception as exc:
                failed += 1
                errors.append(f"{project.id}: {exc}")
        return PresentationBulkResult(
            updated=updated,
            skipped=skipped,
            failed=failed,
            errors=errors,
        )

    # --- Creator assets --------------------------------------------------------
    async def upload_creator_asset(
        self,
        command: CreatorAssetUploadCommand,
    ) -> CreatorAssetResult:
        """Upload + bind a managed creator asset via the creator-asset service.

        Byte-identical to the legacy ``creator-asset/upload``: the route reads the
        file, enforces the size cap, loads + access-checks the project, then this
        handler runs ``service.upload_for_project`` (which validates/normalizes,
        persists, and stages the asset — unchanged).
        """
        asset, project = await self._creator_assets.upload_for_project(command)
        return CreatorAssetResult(asset=asset, project=project)

    async def select_creator_asset(
        self,
        command: CreatorAssetSelectCommand,
    ) -> CreatorAssetResult:
        """Select an existing managed creator asset via the creator-asset service.

        Byte-identical to the legacy ``creator-asset`` select (PUT): the route
        loads + access-checks the project, then this handler runs
        ``service.select_for_project`` (unchanged).
        """
        asset, project = await self._creator_assets.select_for_project(command)
        return CreatorAssetResult(asset=asset, project=project)


@dataclass(frozen=True)
class PresentationCollaborators:
    """Request-scoped collaborators the presentation handlers forward to.

    Grouped into one typed bundle so the handler constructor keeps to a single
    grouped argument beyond the ACL (backend/CLAUDE.md ≤3 args). All are built at
    the inbound edge from the existing infrastructure (no relocation): the generic
    carousel repository (read-only queries the legacy presentation routes issued),
    the refinement service, the strategy registry, and the creator-asset service.
    """

    repository: CarouselRepository
    refinement: CarouselRefinementService
    registry: SlideLayoutRegistry
    creator_assets: CreatorAssetService


__all__ = [
    "CreatorAssetResult",
    "PresentationBulkResult",
    "PresentationCollaborators",
    "PresentationHandlers",
    "SlideMissingPredicate",
]
