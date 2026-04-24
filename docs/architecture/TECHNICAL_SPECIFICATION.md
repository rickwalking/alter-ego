# RAG Backend - Technical Specification

## 1. Detailed Technology Stack

### Core Framework & Runtime
```toml
[project]
name = "rag-backend"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    # Web Framework
    "fastapi==0.115.0",
    "uvicorn[standard]==0.32.0",
    "websockets==13.1",
    "python-multipart==0.0.12",  # For file uploads

    # Data Validation & Settings
    "pydantic==2.9.0",
    "pydantic-settings==2.5.0",
    "email-validator==2.2.0",

    # LangChain & LLM
    "langchain==0.3.0",
    "langchain-core==0.3.0",
    "langchain-openai==0.2.0",
    "langchain-anthropic==0.2.0",
    "langchain-pinecone==0.2.0",
    "langchain-text-splitters==0.3.0",
    "langchain-community==0.3.0",

    # Vector Database
    "pinecone-client[grpc]==5.0.0",

    # Document Processing
    "pypdf==5.0.0",
    "unstructured==0.15.0",
    "unstructured[pdf]==0.15.0",
    "python-magic==0.4.27",
    "aiofiles==24.1.0",

    # Database
    "sqlalchemy[asyncio]==2.0.35",
    "asyncpg==0.29.0",
    "alembic==1.13.0",

    # Caching & Message Queue
    "redis==5.0.0",
    "aioredis==2.0.1",
    "celery==5.4.0",

    # HTTP Client
    "httpx==0.27.0",
    "aiohttp==3.10.0",

    # Utilities
    "python-dotenv==1.0.0",
    "structlog==24.4.0",
    "tenacity==9.0.0",  # Retry logic
    "orjson==3.10.0",   # Fast JSON serialization
    "ulid-py==1.1.0",   # Unique IDs

    # Security
    "python-jose[cryptography]==3.3.0",
    "passlib[bcrypt]==1.7.4",
    "bcrypt==4.2.0",
]

[project.optional-dependencies]
dev = [
    # Testing
    "pytest==8.3.0",
    "pytest-asyncio==0.24.0",
    "pytest-cov==5.0.0",
    "pytest-mock==3.14.0",
    "pytest-xdist==3.6.0",      # Parallel test execution
    "factory-boy==3.3.0",        # Test data generation
    "faker==28.0.0",             # Fake data
    "respx==0.21.0",             # HTTPX mocking
    "asgi-lifespan==2.1.0",      # ASGI lifespan testing
    "testcontainers==4.8.0",     # Integration testing with Docker

    # Code Quality
    "ruff==0.6.0",               # Linting & formatting
    "mypy==1.11.0",              # Type checking
    "pre-commit==3.8.0",         # Git hooks

    # Debugging
    "debugpy==1.8.0",
    "ipdb==0.13.0",
    "rich==13.8.0",              # Pretty printing
]

[tool.ruff]
target-version = "py311"
line-length = 88
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
addopts = "-v --tb=short --strict-markers"
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "slow: Slow tests",
]
```

---

## 2. Clean Architecture Folder Structure

```
rag-backend/
├── pyproject.toml                 # Dependencies & tool config
├── .env.example                   # Environment variables template
├── .env                           # Local environment (gitignored)
├── Makefile                       # Common commands
├── README.md
├── docker-compose.yml
├── Dockerfile
│
├── src/                           # Source code (package)
│   └── rag_backend/              # Main package
│       ├── __init__.py
│       ├── main.py               # FastAPI app entry point
│       ├── container.py          # Dependency injection container
│       │
│       ├── domain/               # Domain layer (business logic)
│       │   ├── __init__.py
│       │   ├── models/           # Domain entities
│       │   │   ├── __init__.py
│       │   │   ├── document.py
│       │   │   ├── conversation.py
│       │   │   └── chat.py
│       │   ├── protocols/        # Interfaces (Python Protocols)
│       │   │   ├── __init__.py
│       │   │   ├── repositories.py
│       │   │   ├── services.py
│       │   │   └── retrievers.py
│       │   ├── exceptions/       # Domain exceptions
│       │   │   ├── __init__.py
│       │   │   ├── document.py
│       │   │   └── chat.py
│       │   └── value_objects/    # Value objects
│       │       ├── __init__.py
│       │       └── search.py
│       │
│       ├── application/          # Application layer (use cases)
│       │   ├── __init__.py
│       │   ├── interfaces/       # Application interfaces
│       │   │   ├── __init__.py
│       │   │   └── handlers.py
│       │   ├── commands/         # CQRS Commands
│       │   │   ├── __init__.py
│       │   │   ├── document.py
│       │   │   └── chat.py
│       │   ├── queries/          # CQRS Queries
│       │   │   ├── __init__.py
│       │   │   ├── search.py
│       │   │   └── document.py
│       │   └── services/         # Application services
│       │       ├── __init__.py
│       │       ├── chat_service.py
│       │       └── document_service.py
│       │
│       ├── infrastructure/       # Infrastructure layer
│       │   ├── __init__.py
│       │   ├── config/           # Configuration
│       │   │   ├── __init__.py
│       │   │   └── settings.py
│       │   ├── persistence/      # Database implementations
│       │   │   ├── __init__.py
│       │   │   ├── database.py
│       │   │   ├── models/       # SQLAlchemy models
│       │   │   │   ├── __init__.py
│       │   │   │   ├── base.py
│       │   │   │   ├── document.py
│       │   │   │   └── conversation.py
│       │   │   └── repositories/ # Repository implementations
│       │   │       ├── __init__.py
│       │   │       ├── document.py
│       │   │       └── conversation.py
│       │   ├── vector_store/     # Vector DB implementations
│       │   │   ├── __init__.py
│       │   │   ├── pinecone_client.py
│       │   │   └── hybrid_retriever.py
│       │   ├── llm/              # LLM implementations
│       │   │   ├── __init__.py
│       │   │   ├── agent.py
│       │   │   └── embeddings.py
│       │   ├── cache/            # Cache implementations
│       │   │   ├── __init__.py
│       │   │   └── redis_cache.py
│       │   └── logging/          # Logging setup
│       │       ├── __init__.py
│       │       └── config.py
│       │
│       └── api/                  # Presentation layer (API)
│           ├── __init__.py
│           ├── dependencies.py   # FastAPI dependencies
│           ├── middleware/       # Custom middleware
│           │   ├── __init__.py
│           │   ├── error_handler.py
│           │   └── logging.py
│           ├── routers/          # API routes
│           │   ├── __init__.py
│           │   ├── chat.py
│           │   ├── documents.py
│           │   ├── search.py
│           │   └── health.py
│           ├── schemas/          # Pydantic schemas
│           │   ├── __init__.py
│           │   ├── requests/
│           │   │   ├── __init__.py
│           │   │   ├── chat.py
│           │   │   └── document.py
│           │   └── responses/
│           │       ├── __init__.py
│           │       ├── chat.py
│           │       ├── document.py
│           │       └── search.py
│           └── websocket/        # WebSocket handlers
│               ├── __init__.py
│               └── chat.py
│
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures
│   ├── unit/                    # Unit tests
│   │   ├── __init__.py
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   └── test_models.py
│   │   ├── application/
│   │   │   ├── __init__.py
│   │   │   └── test_services.py
│   │   └── infrastructure/
│   │       ├── __init__.py
│   │       └── test_retrievers.py
│   ├── integration/             # Integration tests
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── test_chat_api.py
│   │   └── infrastructure/
│   │       ├── __init__.py
│   │       └── test_pinecone.py
│   ├── e2e/                     # End-to-end tests
│   │   ├── __init__.py
│   │   └── test_chat_flow.py
│   └── fixtures/                # Test fixtures
│       ├── __init__.py
│       ├── documents.py
│       └── conversations.py
│
├── alembic/                      # Database migrations
│   ├── versions/
│   ├── env.py
│   └── alembic.ini
│
└── scripts/                      # Utility scripts
    ├── setup.sh
    ├── migrate.sh
    └── seed.py
```

---

## 3. Protocol-Based Contracts (Dependency Inversion)

### Domain Protocols

```python
# src/rag_backend/domain/protocols/repositories.py
from typing import Protocol, List, Optional
from uuid import UUID

from rag_backend.domain.models.document import Document
from rag_backend.domain.models.conversation import Conversation


class DocumentRepository(Protocol):
    """Protocol for document persistence operations."""

    async def get_by_id(self, document_id: UUID) -> Optional[Document]:
        """Retrieve document by ID."""
        ...

    async def get_all(
        self,
        limit: int = 20,
        offset: int = 0,
        search: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Document]:
        """List documents with filtering."""
        ...

    async def save(self, document: Document) -> Document:
        """Save or update document."""
        ...

    async def delete(self, document_id: UUID) -> bool:
        """Delete document by ID."""
        ...

    async def exists(self, document_id: UUID) -> bool:
        """Check if document exists."""
        ...


class ConversationRepository(Protocol):
    """Protocol for conversation persistence operations."""

    async def get_by_id(self, conversation_id: UUID) -> Optional[Conversation]:
        """Retrieve conversation by ID."""
        ...

    async def save(self, conversation: Conversation) -> Conversation:
        """Save or update conversation."""
        ...

    async def delete(self, conversation_id: UUID) -> bool:
        """Delete conversation by ID."""
        ...
```

```python
# src/rag_backend/domain/protocols/retrievers.py
from typing import Protocol, List
from dataclasses import dataclass

from rag_backend.domain.models.document import DocumentChunk


@dataclass
class SearchQuery:
    """Value object for search queries."""
    query: str
    top_k: int = 5
    alpha: float = 0.5  # Hybrid weight
    filter_tags: List[str] | None = None


@dataclass
class SearchResult:
    """Value object for search results."""
    chunk: DocumentChunk
    score: float
    search_type: str  # "dense", "sparse", "hybrid"


class HybridRetriever(Protocol):
    """Protocol for hybrid search operations."""

    async def retrieve(self, query: SearchQuery) -> List[SearchResult]:
        """Perform hybrid search and return ranked results."""
        ...

    async def add_documents(self, chunks: List[DocumentChunk]) -> List[str]:
        """Index document chunks for search."""
        ...

    async def delete_documents(self, chunk_ids: List[str]) -> bool:
        """Remove document chunks from index."""
        ...
```

```python
# src/rag_backend/domain/protocols/services.py
from typing import Protocol, AsyncIterator
from uuid import UUID

from rag_backend.domain.models.chat import ChatMessage, ChatResponse


class ChatService(Protocol):
    """Protocol for chat operations."""

    async def send_message(
        self,
        conversation_id: UUID,
        message: str
    ) -> ChatResponse:
        """Send message and get response (non-streaming)."""
        ...

    async def stream_message(
        self,
        conversation_id: UUID,
        message: str
    ) -> AsyncIterator[ChatResponse]:
        """Send message and stream response tokens."""
        ...


class DocumentService(Protocol):
    """Protocol for document operations."""

    async def upload_document(
        self,
        file_content: bytes,
        filename: str,
        title: str,
        tags: List[str]
    ) -> Document:
        """Process and store uploaded document."""
        ...

    async def delete_document(self, document_id: UUID) -> bool:
        """Delete document and its chunks."""
        ...
```

---

## 4. Dependency Injection Container

```python
# src/rag_backend/container.py
"""Dependency injection container using dependency-injector."""

from dependency_injector import containers, providers

from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.persistence.database import Database
from rag_backend.infrastructure.persistence.repositories.document import (
    SQLDocumentRepository
)
from rag_backend.infrastructure.vector_store.pinecone_client import (
    PineconeVectorStore
)
from rag_backend.infrastructure.vector_store.hybrid_retriever import (
    PineconeHybridRetriever
)
from rag_backend.infrastructure.llm.agent import LangChainAgent
from rag_backend.application.services.chat_service import ChatApplicationService
from rag_backend.application.services.document_service import (
    DocumentApplicationService
)


class Container(containers.DeclarativeContainer):
    """Application container for dependency injection."""

    # Configuration
    settings = providers.Singleton(Settings)

    # Infrastructure
    database = providers.Singleton(
        Database,
        connection_string=settings.provided.database_url
    )

    vector_store = providers.Singleton(
        PineconeVectorStore,
        api_key=settings.provided.pinecone_api_key,
        index_name=settings.provided.pinecone_index_name
    )

    # Repositories
    document_repository = providers.Factory(
        SQLDocumentRepository,
        session_factory=database.provided.session_factory
    )

    # Retrievers
    hybrid_retriever = providers.Factory(
        PineconeHybridRetriever,
        vector_store=vector_store,
        alpha=settings.provided.hybrid_alpha
    )

    # LLM / Agent
    chat_agent = providers.Factory(
        LangChainAgent,
        retriever=hybrid_retriever,
        openai_api_key=settings.provided.openai_api_key,
        model=settings.provided.llm_model
    )

    # Application Services
    chat_service = providers.Factory(
        ChatApplicationService,
        agent=chat_agent,
        conversation_repository=document_repository  # Will be replaced
    )

    document_service = providers.Factory(
        DocumentApplicationService,
        repository=document_repository,
        retriever=hybrid_retriever,
        vector_store=vector_store
    )


# Global container instance
container = Container()
```

```python
# src/rag_backend/api/dependencies.py
"""FastAPI dependencies using the DI container."""

from fastapi import Depends, Request
from rag_backend.container import container
from rag_backend.domain.protocols.repositories import DocumentRepository
from rag_backend.domain.protocols.services import ChatService, DocumentService


def get_chat_service() -> ChatService:
    """Dependency injection for chat service."""
    return container.chat_service()


def get_document_service() -> DocumentService:
    """Dependency injection for document service."""
    return container.document_service()


def get_document_repository() -> DocumentRepository:
    """Dependency injection for document repository."""
    return container.document_repository()


# Type hints for Depends
ChatServiceDep = Depends(get_chat_service)
DocumentServiceDep = Depends(get_document_service)
DocumentRepositoryDep = Depends(get_document_repository)
```

---

## 5. Pytest Testing Structure

### Test Configuration

```python
# tests/conftest.py
"""Pytest configuration and fixtures."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from rag_backend.domain.models.document import Document, DocumentChunk
from rag_backend.domain.protocols.repositories import DocumentRepository
from rag_backend.domain.protocols.retrievers import HybridRetriever


# Domain Fixtures
@pytest.fixture
def sample_document():
    """Create a sample document for testing."""
    return Document(
        id=uuid4(),
        title="Test Document",
        content="This is test content",
        tags=["test", "sample"],
        chunk_count=3
    )


@pytest.fixture
def sample_chunks():
    """Create sample document chunks."""
    return [
        DocumentChunk(
            id=str(uuid4()),
            content=f"Chunk {i} content",
            metadata={"index": i}
        )
        for i in range(3)
    ]


# Mock Protocols
@pytest.fixture
def mock_document_repository():
    """Mock document repository."""
    repo = MagicMock(spec=DocumentRepository)
    repo.get_by_id = AsyncMock()
    repo.get_all = AsyncMock(return_value=[])
    repo.save = AsyncMock()
    repo.delete = AsyncMock(return_value=True)
    return repo


@pytest.fixture
def mock_hybrid_retriever():
    """Mock hybrid retriever."""
    retriever = MagicMock(spec=HybridRetriever)
    retriever.retrieve = AsyncMock(return_value=[])
    retriever.add_documents = AsyncMock(return_value=[])
    retriever.delete_documents = AsyncMock(return_value=True)
    return retriever


# Integration Fixtures
@pytest_asyncio.fixture
async def test_db():
    """Set up test database."""
    # Setup test database
    from rag_backend.infrastructure.persistence.database import Database

    db = Database("postgresql+asyncpg://test:test@localhost/test_db")
    await db.create_tables()

    yield db

    # Teardown
    await db.drop_tables()


@pytest.fixture
def test_client():
    """Create test client for API tests."""
    from fastapi.testclient import TestClient
    from rag_backend.main import app

    return TestClient(app)
```

### Unit Test Examples

```python
# tests/unit/domain/test_models.py
"""Unit tests for domain models."""

import pytest
from uuid import uuid4

from rag_backend.domain.models.document import Document


class TestDocument:
    """Test cases for Document domain model."""

    def test_document_creation(self):
        """Given valid parameters, when creating document, then success."""
        # Given
        doc_id = uuid4()
        title = "Test Document"

        # When
        document = Document(
            id=doc_id,
            title=title,
            content="Content",
            tags=["test"]
        )

        # Then
        assert document.id == doc_id
        assert document.title == title
        assert document.tags == ["test"]

    def test_document_adds_timestamp(self):
        """Given new document, when created, then has timestamps."""
        # When
        document = Document(
            id=uuid4(),
            title="Test",
            content="Content"
        )

        # Then
        assert document.created_at is not None
        assert document.updated_at is not None


# tests/unit/application/test_services.py
"""Unit tests for application services."""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock

from rag_backend.application.services.document_service import (
    DocumentApplicationService
)
from rag_backend.domain.exceptions.document import DocumentNotFoundError


class TestDocumentService:
    """Test cases for DocumentApplicationService."""

    @pytest.mark.asyncio
    async def test_delete_existing_document(
        self,
        mock_document_repository,
        mock_hybrid_retriever
    ):
        """
        Given existing document,
        when deleting,
        then removes from repository and vector store.
        """
        # Given
        doc_id = uuid4()
        mock_document_repository.get_by_id.return_value = AsyncMock(
            id=doc_id,
            metadata={"chunk_ids": ["chunk1", "chunk2"]}
        )

        service = DocumentApplicationService(
            repository=mock_document_repository,
            retriever=mock_hybrid_retriever,
            vector_store=AsyncMock()
        )

        # When
        result = await service.delete_document(doc_id)

        # Then
        assert result is True
        mock_hybrid_retriever.delete_documents.assert_called_once_with(
            ["chunk1", "chunk2"]
        )
        mock_document_repository.delete.assert_called_once_with(doc_id)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_document(
        self,
        mock_document_repository,
        mock_hybrid_retriever
    ):
        """
        Given non-existent document,
        when deleting,
        then raises DocumentNotFoundError.
        """
        # Given
        doc_id = uuid4()
        mock_document_repository.get_by_id.return_value = None

        service = DocumentApplicationService(
            repository=mock_document_repository,
            retriever=mock_hybrid_retriever,
            vector_store=AsyncMock()
        )

        # When / Then
        with pytest.raises(DocumentNotFoundError):
            await service.delete_document(doc_id)
```

### Integration Test Examples

```python
# tests/integration/api/test_chat_api.py
"""Integration tests for chat API endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient

from rag_backend.main import app


@pytest_asyncio.fixture
async def async_client():
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


class TestChatEndpoints:
    """Integration tests for chat endpoints."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_chat_endpoint_returns_response(self, async_client):
        """
        Given valid chat request,
        when POST /api/chat,
        then returns AI response.
        """
        # Given
        payload = {
            "message": "What is machine learning?",
            "conversation_id": "test-conv-123"
        }

        # When
        response = await async_client.post("/api/chat", json=payload)

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "response" in data["data"]
        assert "sources" in data["data"]
```

### Test Organization

```
tests/
├── conftest.py                    # Shared fixtures
├── pytest.ini                     # Pytest configuration
│
├── unit/                          # Unit tests (fast, isolated)
│   ├── __init__.py
│   ├── conftest.py               # Unit-specific fixtures
│   ├── domain/                   # Domain layer tests
│   │   ├── __init__.py
│   │   ├── test_models.py
│   │   └── test_value_objects.py
│   ├── application/              # Application layer tests
│   │   ├── __init__.py
│   │   ├── test_chat_service.py
│   │   └── test_document_service.py
│   └── infrastructure/           # Infrastructure tests with mocks
│       ├── __init__.py
│       └── test_retrievers.py
│
├── integration/                   # Integration tests (slower, with real deps)
│   ├── __init__.py
│   ├── conftest.py               # Integration fixtures (DB, etc.)
│   ├── api/                      # API endpoint tests
│   │   ├── __init__.py
│   │   ├── test_chat_api.py
│   │   └── test_document_api.py
│   └── infrastructure/           # Real infrastructure tests
│       ├── __init__.py
│       └── test_pinecone.py
│
└── e2e/                          # End-to-end tests (full flows)
    ├── __init__.py
    ├── conftest.py
    └── test_chat_flow.py
```

---

## 6. Running Tests

```bash
# Run all tests
pytest

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run with coverage
pytest --cov=src/rag_backend --cov-report=html --cov-report=term

# Run in parallel
pytest -n auto

# Run specific test file
pytest tests/unit/application/test_services.py

# Run with debugging
pytest --pdb

# Run with verbose output
pytest -v
```

---

## 7. Code Quality Commands

```bash
# Format code
ruff format src tests

# Check linting
ruff check src tests

# Fix auto-fixable issues
ruff check --fix src tests

# Type checking
mypy src

# Run all checks
make check

# Run tests with coverage
make test
```

---

## Summary

This specification provides:

1. **Detailed Dependencies**: Every library with specific versions
2. **Clean Architecture**: Domain-driven folder structure
3. **Protocol-Based Contracts**: Python Protocols for loose coupling
4. **Dependency Injection**: Container-based DI
5. **Pytest Structure**: Organized unit/integration/e2e tests
6. **Code Quality**: Ruff, mypy, pre-commit hooks

**Key Principles:**
- ✅ Dependency Inversion via Protocols
- ✅ Domain-driven clean architecture
- ✅ Pydantic for validation
- ✅ FastAPI with dependency injection
- ✅ Comprehensive pytest suite
