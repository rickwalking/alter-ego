"""Database dependency for FastAPI routes."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.config import get_session_maker


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield the request's session and close it when the request ends.

    The session is opened here rather than delegated to ``get_session``: a nested
    ``async for`` does not close its inner generator when the handler raises, which
    left the session and its connection open until the garbage collector ran.
    """
    async with get_session_maker()() as session:
        yield session
