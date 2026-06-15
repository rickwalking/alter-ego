"""Request-scoped DI provider for the editorial module facade (AE-0110).

This is the HTTP-edge composition point for the editorial bounded context. It
resolves the request-scoped collaborators — the carousel repository (the
``CarouselRepository`` port), the AE-0107 :class:`CarouselProjectWriteOwner`
single write owner, and the AE-0109 :class:`LegacyCarouselAcl` anti-corruption
layer — binds them to the request ``AsyncSession``, wraps that same session in the
platform Unit of Work (the single commit owner, ADR-0009 §9), and hands them to
``bootstrap_module`` to build the public :class:`EditorialModule` facade.

Container resolution happens HERE — at the edge, inside ``api/dependencies/`` —
never inside the module's application code (which composes via ``bootstrap``).
The thin workflow route adapters depend on :func:`get_editorial_workflow_handlers`
(and resolve the workflow engine through the module-level
``build_editorial_workflow_service`` seam in the route module so the AE-0106
safety-net stub still overrides it); they never call ``get_container()`` and never
import the carousel ORM. Mirrors ``api/dependencies/knowledge.py`` and
``api/dependencies/conversation.py`` — except the request session is resolved via
the grandfathered ``get_db`` edge dependency (not ``get_session``) so the module
collaborators share the EXACT same FastAPI-cached ``AsyncSession`` the workflow
routes already depend on (``Depends(get_db)``); a separate ``get_session`` would
yield a second, uncommitted session and break the byte-identical optimistic-lock
+ commit semantics.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.knowledge import get_container
from rag_backend.modules.editorial import (
    CarouselProjectWriteOwner,
    EditorialAdapters,
    EditorialModule,
    EditorialWorkflowHandlers,
    LegacyCarouselAcl,
    bootstrap_module,
)
from rag_backend.platform.database import SqlAlchemyUnitOfWork

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# Defensive guard message for an editorial module bootstrapped without the ACL;
# the edge provider always wires it, so this is a programmer-error sentinel.
_ERR_MODULE_WITHOUT_ACL = "editorial module bootstrapped without the carousel ACL"


def get_editorial_module(
    db: AsyncSession = Depends(get_db),
) -> EditorialModule:
    """Build the request-scoped editorial facade for the current request.

    The same ``AsyncSession`` backs the carousel repository, the AE-0107 write
    owner, the AE-0109 ACL, and the Unit of Work, so the writers' flushes and the
    UoW's single commit share one transaction (ADR-0009 §9).
    """
    container = get_container()
    repository = container.carousel_repository(session=db)
    write_owner = CarouselProjectWriteOwner(db)
    acl = LegacyCarouselAcl(db, write_owner)
    unit_of_work = SqlAlchemyUnitOfWork(db)
    adapters = EditorialAdapters(
        repository=repository,
        unit_of_work=unit_of_work,
        legacy_carousel_acl=acl,
    )
    return bootstrap_module(platform=container, adapters=adapters)


def get_editorial_workflow_handlers(
    module: EditorialModule = Depends(get_editorial_module),
) -> EditorialWorkflowHandlers:
    """Build the request-scoped editorial workflow handlers from the facade.

    The thin ``workflow/state``/``start``/``resume``/``stream`` route adapters
    delegate the engine orchestration + the WO commit to these handlers. The
    handlers read/commit through the ACL (the single ORM seam) bootstrapped on the
    module facade; the route supplies the workflow engine per call (resolved via
    the ``build_editorial_workflow_service`` monkeypatch seam).
    """
    acl = module.legacy_carousel_acl
    if acl is None:  # pragma: no cover - the edge provider always wires the ACL
        raise RuntimeError(_ERR_MODULE_WITHOUT_ACL)
    return EditorialWorkflowHandlers(acl=acl)
