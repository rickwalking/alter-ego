# RAG Backend - Complete Implementation Guide

## 📚 Documentation Overview

This directory contains comprehensive documentation for building the Agentic RAG backend:

| Document | Purpose |
|----------|---------|
| `BACKEND_ARCHITECTURE.md` | High-level system architecture and component interactions |
| `BACKEND_IMPLEMENTATION_PLAN.md` | 4-week development roadmap with detailed milestones |
| `API_CONTRACT.md` | Complete API specification with message formats |
| `TECHNICAL_SPECIFICATION.md` | **Technical implementation details (this doc)** |

---

## 🎯 What Makes This Architecture Special

### 1. **Simplified Clean Architecture**
```
src/rag_backend/
├── domain/           # Business logic, entities, protocols
├── application/      # Use cases, commands, queries
├── infrastructure/   # External implementations
└── api/             # FastAPI routes and schemas
```

### 2. **Protocol-Based Contracts** (Not Abstract Classes)
```python
# Using Python Protocols for loose coupling
class DocumentRepository(Protocol):
    async def get_by_id(self, document_id: UUID) -> Optional[Document]: ...
    async def save(self, document: Document) -> Document: ...

# Implementation in infrastructure layer
class SQLDocumentRepository:
    # Concrete implementation
```

### 3. **Dependency Inversion via Container**
```python
container = Container()
container.document_repository = providers.Factory(SQLDocumentRepository)
container.chat_service = providers.Factory(ChatService, repository=container.document_repository)
```

### 4. **Comprehensive Pytest Structure**
```
tests/
├── unit/           # Fast, isolated tests with mocks
├── integration/    # Tests with real dependencies (DB, Pinecone)
└── e2e/           # Full flow tests
```

---

## 🏗️ Clean Architecture Layers

### Domain Layer (Core Business Logic)
```python
# src/rag_backend/domain/models/document.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from uuid import UUID, uuid4

@dataclass
class Document:
    """Domain entity representing a document."""
    title: str
    content: str | None = None
    tags: List[str] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def add_tag(self, tag: str) -> None:
        """Add a tag to the document."""
        if tag not in self.tags:
            self.tags.append(tag)

    def update_content(self, new_content: str) -> None:
        """Update document content."""
        self.content = new_content
        self.updated_at = datetime.utcnow()
```

### Application Layer (Use Cases)
```python
# src/rag_backend/application/services/document_service.py
from rag_backend.domain.protocols.repositories import DocumentRepository
from rag_backend.domain.protocols.retrievers import HybridRetriever

class DocumentApplicationService:
    """
    Application service coordinating document operations.
    Follows Command Pattern for write operations.
    """

    def __init__(
        self,
        repository: DocumentRepository,  # Injected via Protocol
        retriever: HybridRetriever,      # Injected via Protocol
        vector_store: VectorStore
    ):
        self._repository = repository
        self._retriever = retriever
        self._vector_store = vector_store

    async def upload_document(
        self,
        file_content: bytes,
        filename: str,
        title: str,
        tags: List[str]
    ) -> Document:
        """
        Command: Upload and process a document.

        Steps:
        1. Save file to storage
        2. Extract text content
        3. Split into chunks
        4. Generate embeddings
        5. Index in vector store
        6. Save metadata to database
        """
        # Implementation...
```

### Infrastructure Layer (External Concerns)
```python
# src/rag_backend/infrastructure/persistence/repositories/document.py
from sqlalchemy.ext.asyncio import AsyncSession
from rag_backend.domain.models.document import Document as DomainDocument
from rag_backend.infrastructure.persistence.models.document import (
    Document as DBDocument
)

class SQLDocumentRepository:
    """
    Concrete implementation of DocumentRepository protocol.
    Depends on SQLAlchemy, isolated from domain logic.
    """

    def __init__(self, session_factory: Callable[[], AsyncSession]):
        self._session_factory = session_factory

    async def get_by_id(self, document_id: UUID) -> Optional[DomainDocument]:
        async with self._session_factory() as session:
            db_doc = await session.get(DBDocument, document_id)
            return self._to_domain(db_doc) if db_doc else None

    async def save(self, document: DomainDocument) -> DomainDocument:
        async with self._session_factory() as session:
            db_doc = self._to_db_model(document)
            session.add(db_doc)
            await session.commit()
            return document

    def _to_domain(self, db_doc: DBDocument) -> DomainDocument:
        """Map DB model to domain model."""
        return DomainDocument(
            id=db_doc.id,
            title=db_doc.title,
            content=db_doc.content,
            tags=db_doc.tags,
            created_at=db_doc.created_at,
            updated_at=db_doc.updated_at
        )
```

### API Layer (Presentation)
```python
# src/rag_backend/api/routers/documents.py
from fastapi import APIRouter, Depends, UploadFile
from pydantic import BaseModel

from rag_backend.api.dependencies import DocumentServiceDep
from rag_backend.api.schemas.responses.document import DocumentResponse

router = APIRouter(prefix="/api/documents")

class UploadDocumentRequest(BaseModel):
    title: str
    tags: list[str] = []

@router.post("", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile,
    request: UploadDocumentRequest,
    service: DocumentServiceDep  # Injected dependency
) -> DocumentResponse:
    """Upload and process a new document."""
    content = await file.read()

    document = await service.upload_document(
        file_content=content,
        filename=file.filename,
        title=request.title,
        tags=request.tags
    )

    return DocumentResponse(
        id=str(document.id),
        title=document.title,
        tags=document.tags,
        chunk_count=document.chunk_count
    )
```

---

## 🔧 Key Implementation Patterns

### 1. Protocol-Based Dependency Injection
```python
# Define contract (Protocol) in domain
class DocumentRepository(Protocol):
    async def get_by_id(self, document_id: UUID) -> Optional[Document]: ...

# Implement in infrastructure
class SQLDocumentRepository:
    async def get_by_id(self, document_id: UUID) -> Optional[Document]:
        # SQLAlchemy implementation

# Inject via FastAPI Depends
async def get_document(
    doc_id: UUID,
    repo: Annotated[DocumentRepository, Depends(get_repository)]
):
    return await repo.get_by_id(doc_id)
```

### 2. CQRS (Command Query Responsibility Segregation)
```python
# Commands (write operations)
class UploadDocumentCommand:
    file_content: bytes
    filename: str
    title: str

class UploadDocumentHandler:
    async def handle(self, command: UploadDocumentCommand) -> Document:
        # Process upload

# Queries (read operations)
class SearchDocumentsQuery:
    query: str
    top_k: int = 5

class SearchDocumentsHandler:
    async def handle(self, query: SearchDocumentsQuery) -> List[SearchResult]:
        # Perform search
```

### 3. Pydantic Validation
```python
# Request validation
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: str = Field(..., pattern=r"^conv_[a-zA-Z0-9_-]+$")

    @field_validator('message')
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()

# Response serialization
class ChatResponse(BaseModel):
    response: str
    sources: list[Source]
    conversation_id: str
    timestamp: datetime
```

---

## 🧪 Testing Strategy

### Unit Tests (Domain & Application)
```python
# Fast, isolated, no external dependencies
class TestDocumentService:
    async def test_upload_document_saves_to_repository(self):
        # Arrange
        mock_repo = MagicMock(spec=DocumentRepository)
        mock_retriever = MagicMock(spec=HybridRetriever)
        service = DocumentService(mock_repo, mock_retriever)

        # Act
        result = await service.upload_document(...)

        # Assert
        mock_repo.save.assert_called_once()
```

### Integration Tests (Infrastructure)
```python
# Test with real database and services
@pytest.mark.integration
async def test_document_repository_with_postgres(test_db):
    repo = SQLDocumentRepository(test_db)
    document = Document(title="Test")

    saved = await repo.save(document)
    retrieved = await repo.get_by_id(saved.id)

    assert retrieved.title == "Test"
```

### E2E Tests (Full Flows)
```python
# Test complete user workflows
async def test_upload_and_chat_flow(async_client):
    # Upload document
    response = await async_client.post("/api/documents", ...)

    # Ask question about document
    chat_response = await async_client.post("/api/chat", ...)

    # Verify response references document
    assert "document" in chat_response.json()["data"]["response"]
```

---

## 📦 Technology Stack Summary

### Core
- **Python**: 3.11+
- **FastAPI**: 0.115.0 - Web framework
- **Pydantic**: 2.9.0 - Data validation
- **Uvicorn**: 0.32.0 - ASGI server

### AI & ML
- **LangChain**: 0.3.0 - LLM framework
- **LangGraph**: Agent orchestration
- **OpenAI**: GPT-4o / text-embedding-3-large
- **Pinecone**: Hybrid vector search

### Data
- **SQLAlchemy**: 2.0.35 - ORM
- **AsyncPG**: 0.29.0 - Async PostgreSQL
- **Alembic**: 1.13.0 - Migrations
- **Redis**: 5.0.0 - Caching

### Document Processing
- **PyPDF**: 5.0.0 - PDF parsing
- **Unstructured**: 0.15.0 - Document extraction
- **AIOFiles**: 24.1.0 - Async file I/O

### Testing
- **Pytest**: 8.3.0 - Test framework
- **Pytest-Asyncio**: 0.24.0 - Async support
- **Factory-Boy**: 3.3.0 - Test data
- **Testcontainers**: 4.8.0 - Integration testing

### Code Quality
- **Ruff**: 0.6.0 - Linting & formatting
- **MyPy**: 1.11.0 - Type checking
- **Pre-commit**: 3.8.0 - Git hooks

---

## 🚀 Quick Start Commands

```bash
# 1. Setup project
mkdir rag-backend && cd rag-backend
uv init --python 3.11

# 2. Install dependencies
uv add fastapi uvicorn websockets pydantic pydantic-settings
uv add langchain langchain-openai langchain-pinecone
uv add sqlalchemy asyncpg alembic
uv add pytest pytest-asyncio pytest-cov --group dev

# 3. Create folder structure
mkdir -p src/rag_backend/{domain,application,infrastructure,api}
mkdir -p tests/{unit,integration,e2e}

# 4. Run tests
pytest

# 5. Start development server
uvicorn src.rag_backend.main:app --reload
```

---

## 📋 Checklist for Implementation

### Week 1: Foundation
- [ ] Create project structure with all folders
- [ ] Setup `pyproject.toml` with all dependencies
- [ ] Define domain models (Document, Conversation, Chat)
- [ ] Create Protocol interfaces (Repository, Service, Retriever)
- [ ] Setup PostgreSQL with SQLAlchemy models
- [ ] Implement SQLDocumentRepository
- [ ] Write unit tests for domain models

### Week 2: Core Logic
- [ ] Implement document processing pipeline
- [ ] Setup Pinecone hybrid index
- [ ] Implement HybridRetriever with Protocol
- [ ] Create LangChain agent with tools
- [ ] Implement ChatApplicationService
- [ ] Write integration tests for retrievers

### Week 3: API Layer
- [ ] Setup FastAPI application
- [ ] Configure dependency injection container
- [ ] Implement API routes with Pydantic schemas
- [ ] Add WebSocket handler for streaming
- [ ] Implement error handling middleware
- [ ] Write API integration tests

### Week 4: Production
- [ ] Create Dockerfile
- [ ] Setup docker-compose.yml
- [ ] Add health check endpoints
- [ ] Configure logging (structlog)
- [ ] Setup monitoring (LangSmith)
- [ ] Write deployment documentation

---

## 🔗 Integration Points

### Frontend → Backend

**WebSocket Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat/{conversation_id}');

ws.send(JSON.stringify({
  message: "What is machine learning?"
}));

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'token') {
    appendToChat(data.content);
  }
};
```

**HTTP API:**
```javascript
const response = await fetch('/api/documents', {
  method: 'POST',
  body: formData
});
```

---

## 📊 Success Metrics

### Code Quality
- ✅ 90%+ test coverage
- ✅ MyPy strict mode passing
- ✅ Ruff linting clean
- ✅ All tests passing

### Performance
- ⚡ API response < 200ms (non-streaming)
- ⚡ First token < 1s (streaming)
- ⚡ Document processing < 5s per page
- ⚡ Hybrid search < 100ms

### Reliability
- 🔥 99.9% uptime
- 🔥 Graceful error handling
- 🔥 Automatic retries
- 🔥 Health checks passing

---

## 📞 Support Resources

- **LangChain Docs**: https://python.langchain.com/docs/
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Pydantic Docs**: https://docs.pydantic.dev/
- **Pytest Docs**: https://docs.pytest.org/
- **Context7 LangChain**: https://context7.com/websites/langchain/llms.txt

---

## ✅ Ready to Implement!

You now have:
1. ✅ Complete technical specification
2. ✅ Detailed folder structure
3. ✅ Protocol-based architecture
4. ✅ Dependency injection setup
5. ✅ Pytest testing structure
6. ✅ Code quality tools
7. ✅ 4-week implementation plan

**Start with Week 1 in `BACKEND_IMPLEMENTATION_PLAN.md`!** 🚀
