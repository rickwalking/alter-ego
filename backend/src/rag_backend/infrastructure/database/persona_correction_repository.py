"""Repository for persisted persona feedback corrections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.models.persona_correction import (
    PersonaCorrectionModel,
)


@dataclass(frozen=True)
class PersonaCorrectionRecord:
    """Domain-facing correction row."""

    original_text: str
    corrected_text: str
    context: str
    correction_type: str


class _CreateCorrectionParams(TypedDict, total=False):
    """Bundled parameters for creating a persona correction."""

    persona_id: str
    original_text: str
    corrected_text: str
    context: str
    correction_type: str
    project_id: str | None


class PersonaCorrectionRepository:
    """Postgres-backed storage for FeedbackLearningLoop."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        params: _CreateCorrectionParams,
    ) -> None:
        row = PersonaCorrectionModel(
            persona_id=params["persona_id"],
            project_id=params.get("project_id"),
            original_text=params["original_text"],
            corrected_text=params["corrected_text"],
            context=params["context"],
            correction_type=params["correction_type"],
        )
        self._session.add(row)
        await self._session.flush()

    async def list_recent_by_persona(
        self,
        persona_id: str,
        limit: int,
    ) -> list[PersonaCorrectionRecord]:
        stmt = (
            select(PersonaCorrectionModel)
            .where(PersonaCorrectionModel.persona_id == persona_id)
            .order_by(PersonaCorrectionModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [
            PersonaCorrectionRecord(
                original_text=str(row.original_text),
                corrected_text=str(row.corrected_text),
                context=str(row.context),
                correction_type=str(row.correction_type),
            )
            for row in rows
        ]

    async def list_all_by_persona(
        self, persona_id: str
    ) -> list[PersonaCorrectionRecord]:
        stmt = (
            select(PersonaCorrectionModel)
            .where(PersonaCorrectionModel.persona_id == persona_id)
            .order_by(PersonaCorrectionModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [
            PersonaCorrectionRecord(
                original_text=str(row.original_text),
                corrected_text=str(row.corrected_text),
                context=str(row.context),
                correction_type=str(row.correction_type),
            )
            for row in rows
        ]


__all__ = ["PersonaCorrectionRecord", "PersonaCorrectionRepository"]
