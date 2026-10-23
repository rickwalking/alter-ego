"""Workflow-board rows and the archive fields of their cards.

The board lists the caller's carousels (an admin's: all; anyone else's: owned or
reviewed), active or archived only. Each card says whether the caller may
archive it (its owner or an admin, not a reviewer) and, when the archive rules
refuse it now, why.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.clock import utc_now
from rag_backend.domain.constants.carousel_workflow import PHASE_STATUS_PENDING
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.carousel_archive import (
    archive_refusals,
    heartbeat_stale_seconds,
)
from rag_backend.modules.publishing.domain.projections import BoardCard, BoardQuery


async def board_projects(
    session: AsyncSession, board: BoardQuery
) -> list[CarouselProjectModel]:
    """The board's rows (owner-or-reviewer scope), active or archived only."""
    archived = CarouselProjectModel.archived_at
    query = select(CarouselProjectModel).where(
        CarouselProjectModel.phase_status != PHASE_STATUS_PENDING,
        archived.is_not(None) if board.archived else archived.is_(None),
    )
    if board.author_id is not None:
        query = query.where(
            or_(
                CarouselProjectModel.owner_id == board.author_id,
                CarouselProjectModel.assigned_reviewer_id == board.author_id,
            )
        )
    result = await session.execute(query)
    return list(result.scalars().all())


class BoardArchiveFields:
    """Fills ``can_archive`` and ``archive_refusal`` on the board's cards."""

    def __init__(self, board: BoardQuery, refusals: dict[str, str]) -> None:
        self._author_id = board.author_id
        self._refusals = refusals

    @classmethod
    async def load(
        cls,
        session: AsyncSession,
        board: BoardQuery,
        projects: Sequence[CarouselProjectModel],
    ) -> BoardArchiveFields:
        """Read the archive refusals of ``projects`` in one query."""
        refusals = await archive_refusals(
            session,
            [str(project.id) for project in projects],
            (utc_now(), heartbeat_stale_seconds()),
        )
        return cls(board, refusals)

    def apply(self, card: BoardCard, project: CarouselProjectModel) -> BoardCard:
        """``card`` with the caller's archive permission and the refusal, if any."""
        owner = self._author_id is None or str(project.owner_id) == self._author_id
        return replace(
            card, can_archive=owner, archive_refusal=self._refusals.get(card.id)
        )
