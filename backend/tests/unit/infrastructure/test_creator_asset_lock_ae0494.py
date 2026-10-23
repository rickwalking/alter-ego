"""The photo delete locks the asset row before its in-use check.

Gherkin: tests/features/creator_photo_delete_ae0494.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast
from uuid import UUID

from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ClauseElement

from rag_backend.infrastructure.database.creator_asset_repository import (
    PostgresCreatorAssetRepository,
)

_ASSET_ID = UUID("00000000-0000-4000-8000-000000000494")


class _NoRow:
    def scalar_one_or_none(self) -> None:
        return None


@dataclass
class _RecordingSession:
    statements: list[ClauseElement] = field(default_factory=list)

    async def execute(self, statement: ClauseElement) -> _NoRow:
        self.statements.append(statement)
        return _NoRow()


async def test_the_asset_row_is_read_for_update() -> None:
    """Scenario: A carousel that starts using the photo during a delete keeps it."""
    session = _RecordingSession()
    repository = PostgresCreatorAssetRepository(cast(AsyncSession, session))

    assert await repository.get_for_update(_ASSET_ID) is None

    [statement] = session.statements
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert sql.rstrip().endswith("FOR UPDATE")
    assert "carousel_creator_assets.id = " in sql
