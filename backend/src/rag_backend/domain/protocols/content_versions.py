"""Persistence port of the carousel copy version history."""

from __future__ import annotations

from typing import Protocol

from rag_backend.domain.models.carousel_copy_version import (
    CopyVersion,
    NewCopyVersion,
    VersionPage,
)


class CopyVersionStore(Protocol):
    """Stores and reads the caption / LinkedIn versions of one carousel.

    ``add`` stages the rows in the caller's session without committing, so the
    versions land in the same transaction as the saved texts.
    """

    async def list_versions(
        self, project_id: str, page: VersionPage
    ) -> list[CopyVersion]:
        """One page of the carousel's versions, newest first."""
        ...

    async def latest_texts(self, project_id: str) -> dict[str, str]:
        """The newest stored text of each field that has versions."""
        ...

    async def get_version(self, project_id: str, number: int) -> CopyVersion | None:
        """Version ``number`` of the carousel, or ``None``."""
        ...

    async def add(self, project_id: str, versions: list[NewCopyVersion]) -> None:
        """Stage ``versions`` with the next numbers, in order."""
        ...


__all__ = ["CopyVersionStore"]
