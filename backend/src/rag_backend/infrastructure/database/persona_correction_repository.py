"""Repository for persisted persona feedback corrections."""

from __future__ import annotations

from dataclasses import dataclass

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


class PersonaCorrectionRepository:
    """Postgres-backed storage for FeedbackLearningLoop."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        persona_id: str,
        original_text: str,
        corrected_text: str,
        context: str,
        correction_type: str,
        project_id: str | None = None,
    ) -> None:
        row = PersonaCorrectionModel(
            persona_id=persona_id,
            project_id=project_id,
            original_text=original_text,
            corrected_text=corrected_text,
            context=context,
            correction_type=correction_type,
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
