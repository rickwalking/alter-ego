"""Request-scoped DI provider for the knowledge module facade.

This is the HTTP-edge composition point for the knowledge bounded context. It
resolves the request-scoped collaborators (the document repository, the
document-processing pipeline, and the hybrid retriever) from the DI container,
wraps the request ``AsyncSession`` in the platform Unit of Work (the single
commit owner, ADR-0009 §9), and hands them to ``bootstrap_module`` to build the
public ``KnowledgeService`` facade.

Container resolution happens HERE — at the edge, inside ``api/dependencies/`` —
never inside the module's application code (which composes via ``bootstrap``).
Routes depend on :func:`get_knowledge_service`; they never call
``get_container()`` themselves.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

from rag_backend.infrastructure.container import get_container
from rag_backend.infrastructure.database.config import get_session
from rag_backend.modules.knowledge import (
    KnowledgeAdapters,
    KnowledgeService,
    bootstrap_module,
)
from rag_backend.platform.database import SqlAlchemyUnitOfWork

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def get_knowledge_service(
    db: AsyncSession = Depends(get_session),
) -> KnowledgeService:
    """Build the request-scoped knowledge facade for the current request.

    The same ``AsyncSession`` backs both the repository and the Unit of Work, so
    the repository's flushes and the UoW's single commit share one transaction.
    """
    container = get_container()
    repository = container.document_repository(session=db)
    pipeline = container.document_pipeline(document_repository=repository)
    retriever = container.retriever()
    unit_of_work = SqlAlchemyUnitOfWork(db)
    adapters = KnowledgeAdapters(
        repository=repository,
        pipeline=pipeline,
        retriever=retriever,
        unit_of_work=unit_of_work,
    )
    return bootstrap_module(platform=container, adapters=adapters)
