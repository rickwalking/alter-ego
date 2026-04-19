"""SQLAlchemy database configuration."""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

# Base class for all SQLAlchemy models
Base = declarative_base()

# Engine will be initialized in lifespan
c_engine = None


async def init_db(database_url: str, pool_size: int = 5, max_overflow: int = 10) -> None:
    """Initialize database engine and create tables."""
    global c_engine
    if c_engine is not None:
        return  # Already initialized (e.g., in tests)
    c_engine = create_async_engine(
        database_url,
        echo=False,
        future=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    async with c_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    global c_engine
    if c_engine:
        await c_engine.dispose()


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Get the async session maker."""
    global c_engine
    if not c_engine:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return async_sessionmaker(
        c_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_session() -> AsyncSession:
    """Get a new database session."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        yield session
