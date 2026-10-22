"""Composition of the caption / LinkedIn version store for the copy routes."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.protocols.content_versions import CopyVersionStore
from rag_backend.infrastructure.database.copy_version_repository import (
    PostgresCopyVersionStore,
)


def build_copy_version_store(session: AsyncSession) -> CopyVersionStore:
    """The ``content_versions`` store on the request's session."""
    return PostgresCopyVersionStore(session)


__all__ = ["build_copy_version_store"]
