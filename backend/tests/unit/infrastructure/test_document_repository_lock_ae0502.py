"""The document repository reads a row for update (fake and Postgres adapters).

Scenario: A scope change and a reprocess lock the document row
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.models import Document
from rag_backend.infrastructure.database.document_repository import (
    PostgresDocumentRepository,
)
from tests.unit.infrastructure.test_document_repository_contract import (
    DocumentRepositoryContract,
    FakeDocumentRepository,
)

_FAKE = "fake"
_POSTGRES = "postgres"


@pytest.fixture(params=[_FAKE, _POSTGRES])
def repo(request: pytest.FixtureRequest) -> DocumentRepositoryContract:
    """Each adapter in turn."""
    if request.param == _FAKE:
        return FakeDocumentRepository()
    db_session: AsyncSession = request.getfixturevalue("db_session")
    return PostgresDocumentRepository(db_session)


@pytest.mark.unit
class TestGetByIdForUpdate:
    async def test_returns_the_stored_document(
        self, repo: DocumentRepositoryContract
    ) -> None:
        """Scenario: A scope change and a reprocess lock the document row"""
        created = await repo.create(Document(content="c", title="locked"))

        locked = await repo.get_by_id_for_update(created.id)

        assert locked is not None
        assert locked.id == created.id
        assert locked.title == "locked"

    async def test_unknown_document_is_none(
        self, repo: DocumentRepositoryContract
    ) -> None:
        """Scenario: A scope change and a reprocess lock the document row"""
        assert await repo.get_by_id_for_update(uuid4()) is None


async def test_the_postgres_query_locks_the_row() -> None:
    """Scenario: A scope change and a reprocess lock the document row"""
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)

    await PostgresDocumentRepository(session).get_by_id_for_update(uuid4())

    statement = session.execute.await_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert sql.rstrip().endswith("FOR UPDATE")
