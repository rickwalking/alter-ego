"""Request-scoped DI provider for the identity module handlers.

This is the HTTP-edge composition point for the identity bounded context. It
resolves the request-scoped user repository, wraps the request ``AsyncSession``
in the platform Unit of Work (the single commit owner, ADR-0009 §9), carries the
unchanged JWT ``Settings``, and hands them to ``bootstrap_module`` to build the
public :class:`IdentityServices` facade (the ``auth`` + ``admin`` handlers the
routes delegate to).

Container/session resolution happens HERE — at the edge, inside
``api/dependencies/`` — never inside the module's application code (which
composes via ``bootstrap``). The repository and session are resolved through the
sibling ``api.dependencies.auth`` provider (which already owns the legacy,
grandfathered persistence edges) so this provider adds no new ``api ->
infrastructure`` dependency. The same ``AsyncSession`` backs both the repository
and the Unit of Work, so the repository's flushes and the UoW's single commit
share one transaction. Routes depend on :func:`get_identity_service`; they never
call ``get_container()`` or import a concrete user repository themselves.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.auth import get_request_session, get_user_repo
from rag_backend.infrastructure.config.settings import Settings, get_settings
from rag_backend.modules.identity import (
    IdentityAdapters,
    IdentityServices,
    UserRepository,
    bootstrap_module,
)
from rag_backend.platform.database import SqlAlchemyUnitOfWork


def get_identity_service(
    repository: Annotated[UserRepository, Depends(get_user_repo)],
    session: Annotated[AsyncSession, Depends(get_request_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IdentityServices:
    """Build the request-scoped identity facade for the current request.

    The repository and Unit of Work share the one request ``AsyncSession`` so the
    repository's flushes and the UoW's single commit run in the same transaction.
    """
    unit_of_work = SqlAlchemyUnitOfWork(session)
    adapters = IdentityAdapters(
        repository=repository,
        settings=settings,
        unit_of_work=unit_of_work,
    )
    return bootstrap_module(platform=settings, adapters=adapters)


__all__ = ["get_identity_service"]
