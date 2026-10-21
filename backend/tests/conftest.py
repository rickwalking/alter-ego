"""Pytest configuration and fixtures."""

import os

# Required before any import that loads Settings (e.g. Container) during test collection.
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-suite!!")
os.environ.setdefault("ANON_SECRET_KEY", "test-anon-secret-for-pytest-suite!")

import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

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


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register the Knowledge golden-snapshot capture flag (AE-0088).

    When ``--snapshot-update`` is passed, the Knowledge safety-net snapshot
    tests rewrite the committed golden snapshots from current behavior instead
    of asserting against them.
    """
    parser.addoption(
        "--snapshot-update",
        action="store_true",
        default=False,
        help="Capture/refresh Knowledge golden snapshots from current behavior.",
    )


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


@pytest.fixture
def no_outbox_relay(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Stub the post-commit outbox relay for tests that do not exercise it.

    ``WorkflowEventService`` drains the outbox through the global
    ``db_config.c_engine`` after commit. In tests on ``test_engine`` that global
    is whatever an earlier test installed (often an engine already disposed),
    so the relay would open a connection nothing ever closes (AE-0446).
    """
    from rag_backend.application.services import workflow_event_service

    relay = AsyncMock()
    monkeypatch.setattr(workflow_event_service, "relay_after_commit", relay)
    return relay


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
        # A test that calls session.rollback() already ended this transaction.
        if transaction.is_active:
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


# QA r1 S-W1: the research SSRF guard resolves hostnames before scraping. Tests
# must never touch real DNS, so every test sees a public answer unless it
# passes its own resolver (see tests/unit/domain/test_url_safety.py).
_TEST_PUBLIC_IP = "93.184.216.34"


async def _public_resolver(_host: str) -> tuple[str, ...]:
    return (_TEST_PUBLIC_IP,)


@pytest.fixture(autouse=True)
def _stub_research_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the SSRF guard's system resolver with a fixed public address."""
    from rag_backend.domain import url_safety

    monkeypatch.setattr(url_safety, "system_resolve", _public_resolver)
