"""Database dependency for FastAPI routes."""

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.config import get_session


async def get_db() -> AsyncSession:
    """Get database session for dependency injection."""
    async for session in get_session():
        yield session
