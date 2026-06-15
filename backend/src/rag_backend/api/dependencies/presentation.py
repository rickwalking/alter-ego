"""Request-scoped DI provider for the presentation module facade (AE-0120).

This is the HTTP-edge composition point for the presentation bounded context. It
resolves the request-scoped collaborators — the carousel repository (the
``CarouselRepository`` port), the carousel refinement service, the slide-layout
strategy registry, and the creator-asset service (reused from the existing
carousel route dependencies so their container-override seams are preserved) —
plus the AE-0118 :class:`PresentationWriteOwner` single write owner and the
:class:`PresentationPersistenceAcl` read/write seam, binds them to the request
``AsyncSession``, wraps that same session in the platform Unit of Work (the single
commit owner, ADR-0009 §9), and hands them to ``bootstrap_module`` to build the
public :class:`PresentationModule` facade and its request-scoped
:class:`PresentationHandlers`.

Container resolution happens HERE — at the edge, inside ``api/dependencies/`` —
never inside the module's application code (which composes via ``bootstrap``).
The thin presentation route adapters depend on
:func:`get_presentation_handlers`; they never call ``get_container()`` and never
import the carousel/slide ORM. Mirrors ``api/dependencies/editorial.py`` and
``api/dependencies/knowledge.py``.

The ACL/owner are built on the SAME request ``AsyncSession`` the carousel
repository and the other collaborators already use (FastAPI caches
``Depends(get_session)`` per request), so the writers' flushes and the UoW's
single commit share one transaction — preserving the byte-identical
optimistic-lock + commit semantics the legacy presentation routes had.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.knowledge import get_container, get_session
from rag_backend.api.routes.carousels.deps import (
    get_carousel_refinement,
    get_carousel_repo,
    get_strategy_registry,
)
from rag_backend.application.services.carousel.creator_asset_service import (
    CreatorAssetService,
)
from rag_backend.application.services.carousel_template.strategies.registry import (
    SlideLayoutRegistry,
)
from rag_backend.domain.protocols import (
    CarouselRefinementService,
    CarouselRepository,
)
from rag_backend.modules.presentation import (
    PresentationAdapters,
    PresentationCollaborators,
    PresentationHandlers,
    PresentationModule,
    PresentationPersistenceAcl,
    PresentationWriteOwner,
    bootstrap_module,
)
from rag_backend.platform.database import SqlAlchemyUnitOfWork

# Defensive guard message for a presentation module bootstrapped without the
# handlers; the edge provider always wires the ACL + collaborators, so this is a
# programmer-error sentinel.
_ERR_MODULE_WITHOUT_HANDLERS = "presentation module bootstrapped without handlers"


@dataclass(frozen=True)
class _PresentationEdgeContext:
    """Request-scoped collaborators resolved at the edge (keeps providers ≤3 args).

    Bundles the carousel repository, the refinement service, the strategy
    registry, and the creator-asset service — each resolved via the existing
    carousel route dependencies so their container-override seams are preserved —
    into one typed object the module builder forwards to the facade bootstrap.
    """

    repository: CarouselRepository
    refinement: CarouselRefinementService
    registry: SlideLayoutRegistry
    creator_assets: CreatorAssetService


@dataclass(frozen=True)
class _RegistryAssetBundle:
    """The registry + creator-asset service pair (keeps the resolver ≤3 args)."""

    registry: SlideLayoutRegistry
    creator_assets: CreatorAssetService


def _resolve_creator_asset_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CreatorAssetService:
    """Resolve the creator-asset service via the legacy route-edge factory.

    Imported lazily from the ``creator_assets`` route module to avoid an import
    cycle (that module imports :func:`get_presentation_handlers` from here) while
    keeping the grandfathered ``creator_assets -> creator_asset_repository`` import
    pair under that module. The factory only constructs request-scoped adapters on
    the shared session, so calling it directly is byte-identical to the legacy
    ``Depends(get_creator_asset_service)`` wiring.
    """
    from rag_backend.api.routes.carousels.creator_assets import (
        get_creator_asset_service,
    )

    return get_creator_asset_service(session)


def _resolve_registry_asset_bundle(
    registry: Annotated[SlideLayoutRegistry, Depends(get_strategy_registry)],
    creator_assets: Annotated[
        CreatorAssetService, Depends(_resolve_creator_asset_service)
    ],
) -> _RegistryAssetBundle:
    """Resolve the strategy registry + creator-asset service pair."""
    return _RegistryAssetBundle(registry=registry, creator_assets=creator_assets)


def _resolve_edge_context(
    repository: Annotated[CarouselRepository, Depends(get_carousel_repo)],
    refinement: Annotated[CarouselRefinementService, Depends(get_carousel_refinement)],
    bundle: Annotated[_RegistryAssetBundle, Depends(_resolve_registry_asset_bundle)],
) -> _PresentationEdgeContext:
    """Resolve the request-scoped presentation collaborators (≤3 args)."""
    return _PresentationEdgeContext(
        repository=repository,
        refinement=refinement,
        registry=bundle.registry,
        creator_assets=bundle.creator_assets,
    )


def get_presentation_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    context: Annotated[_PresentationEdgeContext, Depends(_resolve_edge_context)],
) -> PresentationModule:
    """Build the request-scoped presentation facade for the current request.

    The same ``AsyncSession`` backs the carousel repository, the AE-0118 write
    owner, the ACL, the creator-asset/refinement collaborators, and the Unit of
    Work, so the writers' flushes and the UoW's single commit share one
    transaction (ADR-0009 §9).
    """
    write_owner = PresentationWriteOwner(session)
    acl = PresentationPersistenceAcl(session, write_owner)
    unit_of_work = SqlAlchemyUnitOfWork(session)
    adapters = PresentationAdapters(
        repository=context.repository,
        unit_of_work=unit_of_work,
        persistence_acl=acl,
        handler_collaborators=PresentationCollaborators(
            repository=context.repository,
            refinement=context.refinement,
            registry=context.registry,
            creator_assets=context.creator_assets,
        ),
    )
    container = get_container()
    return bootstrap_module(platform=container, adapters=adapters)


def get_presentation_handlers(
    module: Annotated[PresentationModule, Depends(get_presentation_service)],
) -> PresentationHandlers:
    """Build the request-scoped presentation handlers from the facade.

    The thin presentation route adapters (media / preview / strategies / admin /
    creator-asset and the crud project-GET design-token merge) delegate their
    data operations to these handlers. The handlers read/commit through the
    AE-0118 ACL (the single ORM seam) bootstrapped on the module facade; access
    checks + HTTP/FileResponse mapping stay at the route edge.
    """
    handlers = module.handlers
    if handlers is None:
        raise RuntimeError(_ERR_MODULE_WITHOUT_HANDLERS)
    return handlers
