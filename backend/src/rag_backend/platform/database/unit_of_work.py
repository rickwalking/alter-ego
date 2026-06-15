"""Request-scoped Unit of Work — the single transaction owner (ADR-0009 §9).

A Unit of Work wraps the existing per-request :class:`AsyncSession` and is the
**sole committer** for a bounded context's writes during a request. Repositories
only ``flush`` (staging row changes inside the open transaction); the UoW is the
one place that ``commit``\\s or ``rollback``\\s, so there is exactly one
transaction owner per request (ADR-0009: transaction ownership stays with the
UoW/caller, never with repository methods).

The UoW is created by an inbound dependency provider (FastAPI ``Depends`` at the
HTTP edge; explicit construction in workers/agent adapters) and passed to module
handlers via ``bootstrap_module`` — never resolved from a global container
(ADR-0009 §9).

This module lives under ``rag_backend.platform`` (shared technical plumbing),
not under ``infrastructure/database``: the UoW is the transaction *owner*, a
platform concern, whereas the ``infrastructure/database`` adapters are
flush-only repositories that must never commit.
"""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, runtime_checkable

from sqlalchemy.ext.asyncio import AsyncSession


@runtime_checkable
class UnitOfWork(Protocol):
    """Transaction boundary for a single request (the sole commit owner).

    Usable directly via ``commit()``/``rollback()`` or as an async context
    manager. When used as a context manager it commits on a clean exit and
    rolls back if the body raises, guaranteeing no partial writes are persisted
    on failure.
    """

    async def commit(self) -> None:
        """Commit the open transaction."""
        ...

    async def rollback(self) -> None:
        """Roll back the open transaction (no partial writes persisted)."""
        ...

    async def __aenter__(self) -> UnitOfWork:
        """Enter the transaction scope."""
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        """Commit on clean exit; roll back if the body raised."""
        ...


class SqlAlchemyUnitOfWork:
    """``UnitOfWork`` backed by the request-scoped SQLAlchemy ``AsyncSession``.

    Wraps — and does not own the lifecycle of — the session yielded by the
    inbound ``get_session`` dependency. The session's open/close is managed by
    that dependency; this UoW only governs the transaction boundary (commit /
    rollback) so it is the single committer for the request's writes.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """The wrapped request-scoped session (for repository wiring)."""
        return self._session

    async def commit(self) -> None:
        """Commit the open transaction."""
        await self._session.commit()

    async def rollback(self) -> None:
        """Roll back the open transaction (no partial writes persisted)."""
        await self._session.rollback()

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        """Enter the transaction scope."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        """Commit on clean exit; roll back (re-raising) if the body raised."""
        if exc_type is not None:
            await self.rollback()
            return
        await self.commit()
