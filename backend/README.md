# Alter-Ego Backend

A Python-based **Agentic RAG** (Retrieval-Augmented Generation) system with hybrid vector search, built with **FastAPI**, **LangChain**, **LangGraph**, and **Pinecone**. Provides REST and WebSocket APIs for an AI chat application that answers questions using your personal knowledge base.

Part of the **Alter-Ego** full-stack RAG system — see the [root README](../README.md) for the complete architecture.

## Architecture

This backend follows **Clean Architecture** principles with **Protocol-based contracts**:

```
src/rag_backend/
├── domain/                 # Business logic & entities
│   ├── models.py           # Domain entities (Document, Conversation, Message)
│   └── protocols.py        # Protocol interfaces for repositories & services
├── application/            # Use cases & services
│   └── services/
│       ├── conversation_service.py
│       ├── document_pipeline.py
│       └── rag_agent.py    # LangChain agent with tools
├── infrastructure/         # External implementations
│   ├── config/             # Settings & DI container
│   ├── database/           # SQLAlchemy models & repositories
│   ├── external/           # OpenAI, Pinecone clients
│   └── retrieval/          # Hybrid retriever, document processor
└── api/                    # FastAPI routes & middleware
    ├── routes/             # REST endpoints
    ├── schemas.py          # Pydantic models
    └── websocket/          # WebSocket streaming handlers
```

### Design Principles

- **Domain layer** — Entities and Protocol interfaces only, no dependencies
- **Application layer** — Business logic and use cases, depends on domain
- **Infrastructure layer** — Concrete implementations of protocols
- **API layer** — HTTP/WebSocket handlers, depends on application

## Features

- **Hybrid Vector Search** — Dense (semantic) + sparse (keyword) vectors with RRF fusion via Pinecone
- **Agentic RAG** — LangChain/LangGraph agent with document search tools
- **Document Pipeline** — Automatic chunking, embedding, and indexing for PDF/TXT/MD files
- **Conversation Management** — Full CRUD for conversations with message history
- **WebSocket Streaming** — Real-time token-by-token response streaming
- **REST API** — Complete CRUD for documents, conversations, and search
- **Async PostgreSQL** — SQLAlchemy 2.0 with asyncpg
- **Dependency Injection** — Clean separation via dependency-injector
- **Structured Logging** — Structlog for consistent log output

## Tech Stack

| Category | Technology |
|----------|------------|
| Framework | [FastAPI](https://fastapi.tiangolo.com/) |
| Language | Python 3.11+ |
| ORM | [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (async) |
| Database | PostgreSQL 17 |
| Vector Store | [Pinecone](https://www.pinecone.io/) (hybrid search) |
| AI/LLM | [OpenAI](https://openai.com/) (GPT-4o, text-embedding-3-large) |
| Agent Framework | [LangChain](https://python.langchain.com/) + [LangGraph](https://langchain-ai.github.io/langgraph/) |
| Validation | [Pydantic v2](https://docs.pydantic.dev/) |
| DI | [dependency-injector](https://python-dependency-injector.etalab-lab.fr/) |
| Package Manager | [uv](https://docs.astral.sh/uv/) |
| Testing | [pytest](https://docs.pytest.org/) + [pytest-asyncio](https://pytest-asyncio.readthedocs.io/) |
| Linting | [ruff](https://docs.astral.sh/ruff/) + [mypy](https://mypy.readthedocs.io/) (strict) |

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- PostgreSQL 17 running locally
- Pinecone account with API key
- OpenAI API key

### Installation

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/rag_backend --cov-report=html
```

### Environment Variables

Create a `.env` file:

```env
# Database
DATABASE_URL=postgresql+asyncpg://rag_user:rag_password@localhost:5432/rag_db

# Vector Store (Pinecone)
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_INDEX_NAME=rag-index
PINECONE_ENVIRONMENT=us-east-1

# OpenAI
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-large

# LangSmith (optional)
LANGSMITH_API_KEY=your-langsmith-api-key
LANGSMITH_PROJECT=rag-backend

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=true
```

### Running the Server

```bash
uv run python -m rag_backend.main
```

Once running:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health check**: http://localhost:8000/health

## API Reference

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/documents` | Create a document from text content |
| `POST` | `/api/documents/upload` | Upload a file (PDF, TXT, MD) |
| `GET` | `/api/documents` | List all documents |
| `GET` | `/api/documents/{id}` | Get document details |
| `GET` | `/api/documents/{id}/status` | Get processing status |
| `DELETE` | `/api/documents/{id}` | Delete a document |
| `POST` | `/api/documents/{id}/reprocess` | Reprocess a document |

### Conversations

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/conversations` | Create a new conversation |
| `GET` | `/api/conversations` | List conversations |
| `GET` | `/api/conversations/{id}` | Get conversation details |
| `GET` | `/api/conversations/{id}/messages` | Get conversation messages |
| `DELETE` | `/api/conversations/{id}` | Delete a conversation |
| `POST` | `/api/conversations/{id}/generate-title` | Auto-generate conversation title |

### Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/search` | Hybrid search (body payload) |
| `GET` | `/api/search` | Hybrid search (query params) |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `ws://localhost:8000/ws/chat/{conversation_id}` | Real-time streaming chat |

### Example Requests

**Create a document:**
```bash
curl -X POST http://localhost:8000/api/documents \
  -H "Content-Type: application/json" \
  -d '{
    "title": "AI Overview",
    "content": "Artificial Intelligence is transforming...",
    "metadata": {"category": "tech"}
  }'
```

**Hybrid search:**
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "what is AI",
    "top_k": 5,
    "alpha": 0.5
  }'
```

**WebSocket chat:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat/{conversation-id}');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.type, data.content);
};
ws.send(JSON.stringify({ content: "What does the document say about AI?" }));
```

## Testing

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=src/rag_backend --cov-report=html

# Run specific test file
uv run pytest tests/unit/domain/test_models.py -v

# Run only unit tests
uv run pytest tests/unit/ -v

# Run only integration tests
uv run pytest tests/integration/ -v
```

### Gherkin Feature Files

Tests are driven by Gherkin scenarios in `tests/features/`:

- `documents.feature` — Document CRUD and processing
- `conversations.feature` — Conversation and message management
- `search.feature` — Hybrid search behavior

## Code Standards

See [AGENTS.md](./AGENTS.md) and [CLAUDE.md](./CLAUDE.md) for detailed guidelines. Key rules:

- **mypy strict mode** — All code must pass type checking
- **No `Any` types** — Use explicit types and Protocols
- **No magic strings** — All literals extracted to constants
- **Early returns** — Guard clauses over nested conditionals
- **Dictionary dispatch** — Replace complex branching with dict lookups
- **Max 400 lines per file** — Split into focused modules
- **90%+ branch coverage** — Focus on branches, not lines

## Development

### Available Commands

| Command | Description |
|---------|-------------|
| `uv run pytest` | Run all tests |
| `uv run pytest --cov=src/rag_backend` | Run with coverage |
| `uv run mypy src/` | Type checking |
| `uv run ruff check src/` | Linting |
| `uv run ruff format src/` | Formatting |
| `uv run python -m rag_backend.main` | Start server |

### Running with Docker

```bash
docker build -t alter-ego-backend .
docker run -p 8000:8000 --env-file .env alter-ego-backend
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/amazing-feature`
3. Write Gherkin scenarios in `tests/features/`
4. Implement the feature with tests
5. Ensure `uv run pytest`, `uv run mypy src/`, and `uv run ruff check src/` all pass
6. Commit with conventional commit message
7. Open a Pull Request

## Related

- [Frontend](../frontend/) — Next.js 16 + React 19 chat UI
- [Architecture Docs](../docs/) — System design and API contracts
- [Deployment Guide](../docs/deployment/) — Production deployment instructions

---

Built with FastAPI, LangChain, and Pinecone
