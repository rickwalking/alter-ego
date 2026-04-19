# CLAUDE.md - Backend

Python FastAPI backend for the Alter-Ego RAG system.

## Project Structure

```
backend/
├── src/rag_backend/
│   ├── api/              # FastAPI routes, middleware, schemas
│   ├── application/      # Services and use cases
│   ├── domain/           # Entities and protocol interfaces
│   └── infrastructure/   # Database, external services, config
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── pyproject.toml
```

## Tech Stack

| Category | Technology |
|----------|-----------|
| Framework | FastAPI + Uvicorn |
| Language | Python 3.11+ |
| Type Checking | mypy (strict mode) |
| Linting | Ruff |
| Testing | pytest + pytest-asyncio |
| AI/ML | LangChain + LangGraph + DeepAgents |
| Vector DB | Pinecone (hybrid search) |
| Database | PostgreSQL + SQLAlchemy (async) |
| Auth | PyJWT + passlib (bcrypt) |
| DI | dependency-injector |
| Logging | structlog |

## Development Commands

```bash
uv run pytest                    # Run tests
uv run pytest --cov=rag_backend  # Coverage report (90%+ required)
uv run mypy src/                 # Type checking (strict mode)
uv run ruff check src/           # Linting
uv run ruff format src/          # Formatting
```

## Code Rules

### Type Safety
- **mypy strict mode enabled** — All code must pass `mypy --strict`
- **No `Any` types** — Use explicit, specific types. Never use `Any`, `object`, or bare `dict`/`list`
- **Use `Protocol` for interfaces** — Not abstract base classes
- **All functions must have explicit return type annotations**
- **Use `TypedDict` for structured dicts**, not `dict[str, Any]`

### Constants
- **No magic strings** — All string literals used in multiple places must be constants
- **Constants live in `constants.py` files** — One per context/module
- **Naming**: `UPPER_SNAKE_CASE`
- Example: `STATUS_PENDING = "pending"`, `ERR_NOT_FOUND = "not_found"`

### Control Flow
- **Early returns** — Use guard clauses, avoid nested `if` statements
- **Complex conditionals** — For complex branching logic, use dictionaries mapping keys to lambda functions:
  ```python
  handlers: dict[str, Callable[[], None]] = {
      "create": lambda: self._handle_create(),
      "update": lambda: self._handle_update(),
      "delete": lambda: self._handle_delete(),
  }
  handlers.get(action, lambda: self._handle_unknown())()
  ```
- **Max 20 lines per function** — Extract complex logic into focused functions

### File Organization
- **Max 400 lines per file** — Split large files into focused modules
- **Protocols in `domain/protocols.py`** — One file per category (e.g., `protocols/repository.py`, `protocols/services.py`)
- **Pydantic models in `api/schemas.py`** — Grouped by category with clear section comments
- **Constants in `constants.py`** per module/context

### Architecture
- **Clean Architecture** — Domain → Application → Infrastructure → API
- **Dependency Inversion** — Domain defines protocols, infrastructure implements them
- **Protocol-based contracts** — Use `typing.Protocol`, not ABCs
- **Async-first** — All I/O operations must be async

### Testing
- **90%+ branch coverage required** — Focus on branches, not just lines
- **Gherkin-first** — Write `.feature` files before implementing tests
  - See `tests/features/` for scenario definitions
  - Tests must reference Gherkin scenarios in comments
- **Test behavior, not implementation**
- **Mock external dependencies** (Pinecone, OpenAI, etc.)
- **Use SQLite in-memory for database tests**
- **Test structure**:
  ```python
  # Scenario: Given X, when Y, then Z (see features/documents.feature)
  async def test_create_document(self, client):
      ...
  ```

### Logging
- **Use structlog** — Not standard `logging` or `print`
- **Structured fields** — Include context: `logger.info("event", key=value)`
- **Request ID** — Propagated via `X-Request-ID` header

### Security
- **No secrets in code** — Use environment variables via Pydantic Settings
- **JWT authentication** — Use `api/middleware/auth.py` dependencies
- **Input validation** — All inputs validated with Pydantic
- **SQL injection** — Use SQLAlchemy ORM, never raw SQL with string interpolation

## Documentation References

- **Architecture**: `../docs/architecture/`
- **Implementation Plan**: `../docs/backend/`
- **API Contract**: `../docs/architecture/API_CONTRACT.md`
- **Deployment**: `../docs/deployment/`
