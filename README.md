# Alter-Ego

A full-stack **RAG** (Retrieval-Augmented Generation) system that lets you chat with an AI assistant powered by your personal knowledge base. Upload documents, ask questions, and get intelligent answers grounded in your content.

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Frontend      │  REST   │    Backend       │  async  │   PostgreSQL    │
│   Next.js 16    │◄───────►│    FastAPI       │◄───────►│   (conversations│
│   React 19      │  WS     │    LangChain     │         │    messages)    │
│   TypeScript    │         │    LangGraph     │         └─────────────────┘
│   Tailwind v4   │         │    Pinecone      │         ┌─────────────────┐
└─────────────────┘         └──────────────────┘  hybrid │   Pinecone      │
                                                        │ (vector search) │
                                                        └─────────────────┘
```

### Components

| Component | Directory | Tech Stack |
|-----------|-----------|------------|
| **Frontend** | [`frontend/`](./frontend/) | Next.js 16, React 19, TypeScript, Tailwind v4, TanStack Query |
| **Backend** | [`backend/`](./backend/) | FastAPI, LangChain, LangGraph, Pinecone, PostgreSQL, SQLAlchemy 2.0 |
| **Docs** | [`docs/`](./docs/) | Architecture, deployment, and development guides |
| **Infrastructure** | `docker-compose.yml` | PostgreSQL, backend, frontend services |

## Quick Start

### Prerequisites

- Node.js 22+ and npm
- Python 3.11+ and [uv](https://docs.astral.sh/uv/)
- PostgreSQL 17
- [Pinecone](https://www.pinecone.io/) account
- [OpenAI](https://openai.com/) API key

### Run with Docker Compose

```bash
# Clone the repository
git clone <repository-url>
cd alter-ego

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Start all services
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Run Locally

**Backend:**
```bash
cd backend
uv sync
# Create .env with your DATABASE_URL, OPENAI_API_KEY, PINECONE_API_KEY
uv run python -m rag_backend.main
```

**Frontend:**
```bash
cd frontend
npm install
# Create .env.local with NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

## Features

- **AI-Powered Chat** — Natural conversations with an AI that understands your documents via RAG
- **Hybrid Search** — Dense (semantic) + sparse (keyword) vector search with RRF fusion
- **Document Management** — Upload PDF, TXT, and MD files with automatic chunking and indexing
- **Real-time Streaming** — Token-by-token response streaming via WebSockets
- **Conversation History** — Full CRUD for conversations with message persistence
- **Dark Mode** — System-aware theme toggling
- **Internationalization** — Full i18n support (English, Portuguese ready)
- **Responsive Design** — Works on desktop, tablet, and mobile
- **Accessibility** — WCAG 2.1 AA compliant

## Project Structure

```
alter-ego/
├── frontend/               # Next.js React frontend
│   ├── src/
│   │   ├── app/            # App Router with route groups
│   │   │   ├── (public)/   # Public routes (home page)
│   │   │   └── (dashboard)/# Authenticated routes (chat, knowledge)
│   │   ├── components/     # UI primitives, layout, providers
│   │   ├── features/       # Feature modules (chat, knowledge)
│   │   ├── lib/            # Utilities, API client
│   │   ├── schemas/        # Zod validation schemas
│   │   ├── i18n/           # Internationalization
│   │   └── constants/      # Application constants
│   ├── tests/              # Playwright E2E + Gherkin features
│   └── README.md           # Frontend-specific docs
├── backend/                # FastAPI RAG backend
│   ├── src/rag_backend/
│   │   ├── domain/         # Entities and Protocol interfaces
│   │   ├── application/    # Services and use cases
│   │   ├── infrastructure/ # Database, Pinecone, OpenAI implementations
│   │   └── api/            # FastAPI routes, WebSocket, schemas
│   ├── tests/              # pytest unit + integration tests
│   └── README.md           # Backend-specific docs
├── docs/                   # Shared documentation
│   ├── architecture/       # System design and API contracts
│   ├── backend/            # Backend-specific guides
│   ├── frontend/           # Frontend-specific guides
│   ├── guides/             # General development guides
│   └── deployment/         # Production deployment guides
└── docker-compose.yml      # Full-stack Docker orchestration
```

## Development

### Code Standards

Both projects enforce strict coding standards:

- **Type safety** — TypeScript strict mode (frontend), mypy strict (backend)
- **No magic strings** — All literals extracted to named constants
- **No hardcoded text** — All user-facing text via i18n
- **90%+ branch coverage** — Gherkin-driven testing
- **Max 400 lines per file** — Split into focused modules
- **Early returns** — Guard clauses over nested conditionals
- **Conventional commits** — `feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`

See each project's `AGENTS.md` and `CLAUDE.md` for detailed guidelines.

### Testing

**Frontend:**
```bash
cd frontend
npm test              # Unit tests (Vitest)
npm run test:coverage # Coverage report
npm run test:e2e      # E2E tests (Playwright)
```

**Backend:**
```bash
cd backend
uv run pytest              # All tests
uv run pytest --cov        # Coverage report
uv run mypy src/           # Type checking
uv run ruff check src/     # Linting
```

## Deployment

### Environment Variables

| Variable | Component | Description |
|----------|-----------|-------------|
| `DATABASE_URL` | Backend | PostgreSQL connection string |
| `OPENAI_API_KEY` | Backend | OpenAI API key for LLM and embeddings |
| `PINECONE_API_KEY` | Backend | Pinecone vector database API key |
| `NEXT_PUBLIC_API_URL` | Frontend | Backend API base URL |

### Docker Compose (Production)

```bash
docker-compose up -d --build
```

### Individual Deployment

- **Frontend**: Deploy to Vercel (`vercel` CLI) or any Node.js host
- **Backend**: Deploy to any Python host (Fly.io, Railway, AWS ECS)
- **Database**: Managed PostgreSQL (Supabase, Neon, RDS)
- **Vector Store**: Pinecone cloud (serverless)

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Write Gherkin scenarios before implementation
4. Ensure all tests, type checks, and linters pass
5. Commit with a conventional commit message
6. Open a Pull Request

## License

MIT
