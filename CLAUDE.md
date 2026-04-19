# CLAUDE.md - Alter-Ego Project

This is the root configuration for the **Alter-Ego** project — a full-stack RAG (Retrieval-Augmented Generation) system.

## Project Structure

```
alter-ego/
├── backend/          # Python FastAPI RAG backend
├── frontend/         # Next.js React frontend
├── docs/             # All documentation
│   ├── architecture/ # System architecture & API contracts
│   ├── backend/      # Backend-specific guides
│   ├── frontend/     # Frontend-specific guides
│   ├── guides/       # General development guides
│   └── deployment/   # Deployment guides
├── docker-compose.yml
└── CLAUDE.md         # You are here
```

## Universal Rules (Apply to All Sub-Projects)

### Code Quality
- **No magic strings** — Extract all string literals to named constants
- **No `any` / `Any` / `object` types** — Use explicit, specific types
- **Early returns preferred** — Avoid nested `if` statements; use guard clauses
- **Max 400 lines per file** — Split large files into focused modules
- **Constants in dedicated files** — Each context/module gets its own `constants` file

### Testing
- **90%+ coverage required** — Focus on branch coverage, not just line coverage
- **Gherkin-first approach** — Write `.feature` files with scenarios before implementing tests
  - Cover happy paths, edge cases, and failures
  - Tests should reference Gherkin scenarios in comments
- **Test behavior, not implementation**
- **Mock external dependencies**

### Documentation
- All documentation lives in `/docs/` with organized sub-folders
- CLAUDE.md files in sub-projects reference docs via progressive disclosure
- Keep README files concise; link to detailed docs

### Git & Commits
- Conventional commit messages
- One logical change per commit
- No secrets or API keys committed

## Sub-Project Rules

Each sub-project has its own `CLAUDE.md` and `AGENTS.md` with specific rules:

- **`backend/CLAUDE.md`** — Python/FastAPI rules (mypy strict, protocols, constants)
- **`frontend/CLAUDE.md`** — React/Next.js rules (i18n, component patterns, tests)

When working on a sub-project, **always read its local CLAUDE.md first**, then this root file for universal rules.

## Development Commands

### Backend
```bash
cd backend
uv run pytest                    # Run tests
uv run pytest --cov=rag_backend  # Coverage report
uv run mypy src/                 # Type checking
uv run ruff check src/           # Linting
```

### Frontend
```bash
cd frontend
npm run dev                      # Development server
npm run build                    # Production build
npm run test                     # Unit tests
npm run test:e2e                 # E2E tests (Playwright)
npm run typecheck                # TypeScript check
npm run lint                     # ESLint
```

## Architecture Overview

- **Backend**: FastAPI + LangChain Deep Agents + LangGraph + Pinecone (hybrid search) + PostgreSQL
- **Frontend**: Next.js 16 + React 19 + TanStack Query + Tailwind CSS v4 + Zod
- **Communication**: REST API + WebSocket streaming + SSE fallback

See `docs/architecture/` for detailed architecture documents.
