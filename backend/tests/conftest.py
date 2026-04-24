"""Pytest configuration and fixtures."""

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from rag_backend.domain.models import Document
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.document_repository import (
    PostgresDocumentRepository,
)

# Use SQLite in-memory for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test with connection-level transaction rollback.

    Uses a connection-level transaction pattern: all commits within the test
    are part of a single transaction that is rolled back at test end.
    """
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    connection = await test_engine.connect()
    transaction = await connection.begin()
    session = async_session(bind=connection)
    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.fixture
def document_repository(db_session: AsyncSession) -> PostgresDocumentRepository:
    """Create a document repository instance."""
    return PostgresDocumentRepository(db_session)


@pytest.fixture
def carousel_repository(db_session: AsyncSession) -> PostgresCarouselRepository:
    """Create a carousel repository instance."""
    return PostgresCarouselRepository(db_session)


@pytest.fixture
def sample_document() -> Document:
    """Create a sample document for testing."""
    return Document(
        content="This is a test document about artificial intelligence.",
        title="AI Test Document",
        metadata={"category": "test", "tags": ["ai", "testing"]},
    )


@pytest.fixture
def sample_documents() -> list[Document]:
    """Create multiple sample documents for testing."""
    return [
        Document(
            content="Document about machine learning algorithms.",
            title="ML Document 1",
            metadata={"category": "ml"},
        ),
        Document(
            content="Document about deep learning.",
            title="DL Document 2",
            metadata={"category": "dl"},
        ),
        Document(
            content="Document about natural language processing.",
            title="NLP Document 3",
            metadata={"category": "nlp"},
        ),
    ]
