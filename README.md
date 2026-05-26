# Alter-Ego

A full-stack **AI content platform** with RAG-powered chat, human-in-the-loop editorial workflows, and persona-driven content generation. Upload knowledge sources, collaborate on carousels and blog posts through review gates, and publish content that reflects an authentic voice—not generic AI output.

## Architecture

```
┌─────────────────┐   REST/SSE   ┌──────────────────┐   async   ┌─────────────────┐
│   Frontend      │◄────────────►│    Backend       │◄─────────►│   PostgreSQL    │
│   Next.js 16    │              │    FastAPI       │           │ (content, users,│
│   React 19      │              │    LangGraph     │           │  workflow state)│
│   TypeScript    │              │    LangChain     │           └─────────────────┘
│   Tailwind v4   │              │    Redis Streams │           ┌─────────────────┐
└─────────────────┘              └────────┬─────────┘  hybrid  │   Pinecone      │
                                          │                      │ (vector search) │
                                          ▼                      └─────────────────┘
                                   ┌──────────────┐
                                   │   Langfuse   │
                                   │ (LLM traces) │
                                   └──────────────┘
```

### Components

| Component | Directory | Tech Stack |
|-----------|-----------|------------|
| **Frontend** | [`frontend/`](./frontend/) | Next.js 16, React 19, TypeScript, Tailwind v4, TanStack Query, next-intl |
| **Backend** | [`backend/`](./backend/) | FastAPI, LangChain, LangGraph, Pinecone, PostgreSQL, SQLAlchemy 2.0, Redis |
| **Docs** | [`docs/`](./docs/) | Architecture, ADRs, deployment guides, editorial workflow docs |
| **Infrastructure** | `docker-compose.yml` | PostgreSQL, Redis, backend, frontend, Langfuse, nginx (prod) |

## What It Does

Alter-Ego evolved from a RAG chat app into a **professional content platform**:

| Area | Capabilities |
|------|--------------|
| **Knowledge & Chat** | Document upload, hybrid search, RAG chat with SSE streaming |
| **Carousel Editorial Workflow** | 7-phase LangGraph workflow with human approval gates (brief → research → outline → content → design → images → final review → published) |
| **Blog Editorial Pipeline** | Draft → review → approve → publish/schedule, version history, inline comments |
| **Persona Engine** | Voice profiles, forbidden phrases, writing samples, voice-match scoring |
| **Quality Rubrics** | Originality, voice match, engagement, clarity scoring with AI + human gates |
| **Collaboration** | Workflow Kanban board, content calendar, notifications, optimistic locking, audit log |
| **Observability** | Langfuse tracing for all LLM calls, workflow failure alerts |

See [`docs/PROFESSIONAL_PIVOT_PLAN.md`](./docs/PROFESSIONAL_PIVOT_PLAN.md) for the full roadmap and [`docs/guides/editorial-workflow-user-guide.md`](./docs/guides/editorial-workflow-user-guide.md) for end-user workflows.

## Quick Start

### Prerequisites

- Node.js 22+ and npm
- Python 3.11+ and [uv](https://docs.astral.sh/uv/)
- Docker and Docker Compose (recommended)
- API keys: [OpenAI](https://openai.com/) and/or [Anthropic](https://anthropic.com/), [Pinecone](https://www.pinecone.io/), optional [Gemini](https://ai.google.dev/)

### Run with Docker Compose (recommended)

```bash
git clone <repository-url>
cd alter-ego

# Backend secrets and API keys
cp backend/.env.example backend/.env
# Edit backend/.env — at minimum set SECRET_KEY, ANON_SECRET_KEY, and your AI provider keys

# Start the full dev stack (postgres, redis, backend, frontend, langfuse)
docker compose up -d --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Langfuse | http://localhost:3001 |

### First-time setup

After the stack is healthy:

```bash
# 1. Run Phase 5 data migration (legacy carousel → editorial workflow schema)
docker cp backend/scripts alter-ego-backend-1:/app/scripts
docker compose exec backend uv run python scripts/migrate_phase5.py

# 2. Bootstrap the first admin user (only when no users exist yet)
docker compose exec backend uv run python -m rag_backend.scripts.bootstrap_admin \
  --email admin@example.com --full-name "Admin User"
```

The bootstrap script prints a one-time temporary password. Change it after first login.

For production deployments with nginx and TLS, use the production overlay:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

For staging/canary rollouts with feature flags, see [`docs/deployment/STAGING_DEPLOY.md`](./docs/deployment/STAGING_DEPLOY.md).

### Run locally (without Docker)

**Backend:**

```bash
cd backend
uv sync
cp .env.example .env   # configure DATABASE_URL and API keys
uv run uvicorn rag_backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**

```bash
cd frontend
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

## Features

### Core Platform

- **AI-Powered Chat** — RAG conversations grounded in your knowledge base
- **Hybrid Search** — Dense (semantic) + sparse (keyword) vectors with RRF fusion via Pinecone
- **Document Management** — Upload PDF, TXT, and MD with automatic chunking and indexing
- **SSE Streaming** — Token-by-token chat and workflow updates via Server-Sent Events
- **Authentication** — JWT-based auth with role-based access (admin, editor, viewer)
- **Internationalization** — English and Portuguese (next-intl)
- **Accessibility** — WCAG 2.1 AA target

### Editorial Workflow (Phases 2–5)

- **Carousel workflow** — LangGraph deep agents with `interrupt()` human gates at each phase
- **Blog workflow** — Submit for review, approve/reject, schedule publish, AI disclosure labels
- **Personas & rubrics** — Voice enforcement and measurable quality criteria
- **Source curation** — Primary sources with synthesis, not web search alone
- **Workflow board** — Kanban view of projects by editorial phase
- **Content calendar** — Scheduled and in-progress content timeline
- **Quality tools** — SEO analysis, accessibility checks, plagiarism detection, AI disclosure
- **Feature flags** — Incremental rollout of editorial, quality, board, and calendar features

## Project Structure

```
alter-ego/
├── frontend/                    # Next.js React frontend
│   ├── src/
│   │   ├── app/                 # App Router (public, dashboard, blog, create)
│   │   ├── components/          # UI primitives, layout, providers
│   │   ├── features/            # chat, blog, create, persona, publish, rubrics, …
│   │   ├── lib/                 # API client, utilities
│   │   ├── i18n/                # en.json, pt.json
│   │   └── constants/           # API endpoints, routes, middleware
│   └── tests/                   # Vitest unit + Playwright E2E
├── backend/
│   ├── src/rag_backend/
│   │   ├── domain/              # Entities, constants, protocols
│   │   ├── application/         # Services, workers, carousel/blog workflows
│   │   ├── agents/              # LangGraph agents, prompts registry
│   │   ├── infrastructure/      # DB, Pinecone, Redis, LLM providers
│   │   └── api/                 # REST routes, SSE streams, middleware
│   ├── alembic/                 # Schema migrations
│   ├── scripts/                 # Phase 5 migration, seed, bootstrap utilities
│   └── tests/                   # pytest unit, integration, Gherkin features
├── docs/
│   ├── architecture/            # System design, API contracts, agent guides
│   ├── decisions/               # Architecture Decision Records (MADR)
│   ├── deployment/              # Staging, production, alerts
│   └── guides/                  # Editorial workflow, QA, testing
├── docker-compose.yml           # Dev stack
├── docker-compose.prod.yml      # Production overlay (nginx, TLS)
├── docker-compose.staging.yml   # Staging with feature flags
└── nginx/                       # Reverse proxy configs
```

## Development

### Code Standards

Both projects enforce strict coding standards:

- **Type safety** — TypeScript strict (frontend), mypy strict (backend)
- **No magic strings** — Constants in dedicated files per module
- **No hardcoded text** — All user-facing strings via i18n (frontend)
- **90%+ branch coverage** — Gherkin-driven testing
- **Max 400 lines per file** — Split into focused modules
- **Conventional commits** — `feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`

See each project's `AGENTS.md` and `CLAUDE.md` for detailed guidelines.

### Testing

**Frontend:**

```bash
cd frontend
npm test                  # Unit tests (Vitest)
npm run test:coverage     # Coverage report
npm run test:e2e          # E2E tests (Playwright)
npm run typecheck         # TypeScript
npm run lint              # ESLint
```

**Backend:**

```bash
cd backend
uv run pytest                    # All tests
uv run pytest --cov=rag_backend  # Coverage report
uv run mypy src/                 # Type checking
uv run ruff check src/           # Linting
```

## Deployment

### Key Environment Variables

| Variable | Component | Description |
|----------|-----------|-------------|
| `DATABASE_URL` | Backend | PostgreSQL connection string |
| `SECRET_KEY` / `ANON_SECRET_KEY` | Backend | JWT signing keys (`openssl rand -hex 32`) |
| `OPENAI_API_KEY` | Backend | OpenAI for embeddings, GPT features |
| `ANTHROPIC_API_KEY` | Backend | Anthropic Claude for creative writing / orchestration |
| `PINECONE_API_KEY` | Backend | Vector database for hybrid search |
| `GEMINI_API_KEY` | Backend | Optional image generation |
| `REDIS_URL` | Backend | Workflow events and caching |
| `LANGFUSE_*` | Backend | LLM trace observability |
| `FEATURE_FLAG_*` | Backend | Toggle editorial workflow features (see staging deploy doc) |
| `NEXT_PUBLIC_API_URL` | Frontend | Backend API base URL |

Full reference: [`backend/.env.example`](./backend/.env.example)

### Deployment Options

| Environment | Command / Doc |
|-------------|---------------|
| **Local dev** | `docker compose up -d --build` |
| **Production** | `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build` |
| **Staging** | [`docs/deployment/STAGING_DEPLOY.md`](./docs/deployment/STAGING_DEPLOY.md) |
| **Frontend only** | Vercel or any Node.js host |
| **Backend only** | Fly.io, Railway, AWS ECS, etc. |

### Post-deploy checklist

1. Run Phase 5 data migration (see [First-time setup](#first-time-setup))
2. Bootstrap admin user or create via `/api/admin/users`
3. Verify health: `curl http://localhost:8000/health/ready`
4. Enable feature flags incrementally in production (see staging deploy doc)

## Documentation

| Document | Description |
|----------|-------------|
| [`docs/PROFESSIONAL_PIVOT_PLAN.md`](./docs/PROFESSIONAL_PIVOT_PLAN.md) | Platform vision and implementation phases |
| [`docs/guides/editorial-workflow-user-guide.md`](./docs/guides/editorial-workflow-user-guide.md) | How to use personas, rubrics, and workflows |
| [`docs/architecture/`](./docs/architecture/) | System design and API contracts |
| [`docs/decisions/`](./docs/decisions/) | Architecture Decision Records |
| [`docs/deployment/`](./docs/deployment/) | Staging, production, and monitoring |
| [`backend/README.md`](./backend/README.md) | Backend-specific setup and API reference |
| [`frontend/README.md`](./frontend/README.md) | Frontend-specific setup and structure |

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Write Gherkin scenarios before implementation
4. Ensure all tests, type checks, and linters pass
5. Commit with a conventional commit message
6. Open a Pull Request

## License

MIT
