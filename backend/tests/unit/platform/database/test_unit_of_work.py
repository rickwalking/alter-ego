"""Unit tests for the request-scoped Unit of Work primitive (AE-0091).

Covers the platform ``SqlAlchemyUnitOfWork``: it is the single commit owner,
delegates commit/rollback to the wrapped ``AsyncSession``, and as an async
context manager commits on clean exit and rolls back (re-raising) on error.

References: tests/features/knowledge_unit_of_work.feature.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.platform.database import SqlAlchemyUnitOfWork, UnitOfWork

_BOOM = "boom"


def _fake_session() -> AsyncMock:
    return AsyncMock(spec=AsyncSession)


class TestSqlAlchemyUnitOfWork:
    """The SQLAlchemy-backed Unit of Work delegates to the wrapped session."""

    def test_satisfies_unit_of_work_protocol(self) -> None:
        # Scenario: SQLAlchemy UoW is a UnitOfWork (knowledge_unit_of_work.feature)
        uow = SqlAlchemyUnitOfWork(_fake_session())
        assert isinstance(uow, UnitOfWork)

    def test_exposes_wrapped_session(self) -> None:
        # The repository wiring reads the same request-scoped session.
        session = _fake_session()
        uow = SqlAlchemyUnitOfWork(session)
        assert uow.session is session

    @pytest.mark.asyncio
    async def test_commit_delegates_to_session(self) -> None:
        # Scenario: the UoW commits -> the wrapped AsyncSession is committed
        session = _fake_session()
        uow = SqlAlchemyUnitOfWork(session)

        await uow.commit()

        session.commit.assert_awaited_once()
        session.rollback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_rollback_delegates_to_session(self) -> None:
        # Scenario: the UoW rolls back -> the wrapped AsyncSession is rolled back
        session = _fake_session()
        uow = SqlAlchemyUnitOfWork(session)

        await uow.rollback()

        session.rollback.assert_awaited_once()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_context_manager_commits_on_clean_exit(self) -> None:
        # Scenario: context exits cleanly -> committed and not rolled back
        session = _fake_session()
        uow = SqlAlchemyUnitOfWork(session)

        async with uow as entered:
            assert entered is uow

        session.commit.assert_awaited_once()
        session.rollback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_context_manager_rolls_back_and_reraises_on_error(self) -> None:
        # Scenario: context exits with an exception -> rolled back, not committed
        session = _fake_session()
        uow = SqlAlchemyUnitOfWork(session)

        with pytest.raises(ValueError, match=_BOOM):
            async with uow:
                raise ValueError(_BOOM)

        session.rollback.assert_awaited_once()
        session.commit.assert_not_awaited()
