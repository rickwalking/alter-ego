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
make regen-contracts             # (repo root) regen + verify all 4 pinned API-contract artifacts
```

After any API-contract change (routes/schemas), run `make regen-contracts` from
the repo root — it regenerates and read-only-verifies all four pinned artifacts
in one fail-fast pass. See
[`docs/guides/api-contract-regen.md`](../docs/guides/api-contract-regen.md)
(AE-0325).

## Code Rules

### Type Safety
- **mypy strict mode enabled** — All code must pass `mypy --strict`
- **No explicit `Any` types** — `disallow_any_explicit = true` in `pyproject.toml`. Use `Protocol`, `TypedDict`, `object`, or `cast` instead.
- **No bare generics** — `disallow_any_generics = true`. Always parameterize `dict`, `list`, `Callable`, etc. (e.g., `dict[str, object]`, `list[int]`).
- **Use `Protocol` for interfaces** — Not abstract base classes
- **All functions must have explicit return type annotations**
- **Use `TypedDict` for structured dicts**, not `dict[str, Any]`
- **Decision tree for dynamic data**: `Protocol` → `object` → `cast(T, value)` → `type: ignore[any]` (last resort, with justification comment)

### Function Signatures
- **Max 3 arguments per function** — Enforced by Ruff `PLR0913` with `max-args = 3`.
- **Use Pydantic for grouped inputs that cross API or service boundaries** — Prefer explicit request/command models over long positional or keyword parameter lists.
- **Use typed command/config objects for internal grouping** — Dataclasses, `TypedDict`, or small domain objects are acceptable when Pydantic validation is not needed.
- **No arbitrary dict bundles** — Grouped inputs must have named fields and static typing.

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
- **Event-driven** — Workflow state changes emit events to Redis Streams
  - Event schema: `{event_id, event_type, aggregate_id, timestamp, version, payload, metadata}`
  - All events must be idempotent (same event processed twice → same result)
  - Consumers use Redis consumer groups for load balancing

### LangGraph / Deep Agents
- **Use Deep Agents** for complex multi-step workflows (carousel, blog post)
- **Use raw LangGraph** for deterministic nodes (formatting, scoring, validation)
- **Use Subagent pattern** for parallel tasks (research, drafting, image generation)
- **Use `interrupt()`** for all human approval gates
- **Never wrap `interrupt()` in bare `try/except`** — always re-raise `GraphInterrupt`
- **Use DeltaChannel** (LangGraph 1.2+) for append-only state to prevent O(N²) checkpoint growth
- **Use PostgresSaver** for production checkpoint persistence
- **Make side effects before `interrupt()` idempotent**
- **Deterministic nodes** — Never use `datetime.now()` or `random()` in graph logic; pass as state

### Testing
- **90%+ branch coverage required** — Focus on branches, not just lines
- **Gherkin-first** — Write `.feature` files before implementing tests
  - See `tests/features/` for scenario definitions
  - Tests must reference Gherkin scenarios in comments
- **Test behavior, not implementation**
- **Mock external dependencies** (Pinecone, OpenAI, etc.)
- **Use SQLite in-memory for database tests**
- **Mutation testing** — `mutmut` runs weekly
  - Target: 70%+ mutation score on business logic modules
  - Use `mutate_only_covered_lines = true` and `type_check_command` to reduce noise
  - Exclude logging statements with `do_not_mutate_patterns`
  - Run incrementally on PRs after 80%+ baseline established
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

## Architecture Decision Records

See `../docs/decisions/` for all ADRs:
- [ADR-002: Use LangGraph for Workflow Engine](../docs/decisions/0002-use-langgraph-for-workflow-engine.md)
- [ADR-003: Implement Persona-Driven AI Content](../docs/decisions/0003-implement-persona-driven-ai-content.md)
- [ADR-004: Adopt Event-Driven Architecture](../docs/decisions/0004-adopt-event-driven-architecture.md)
- [ADR-005: Adopt Mutation Testing](../docs/decisions/0005-adopt-mutation-testing.md)
- [ADR-006: Use JSONB for Rich Content](../docs/decisions/0006-use-jsonb-for-rich-content.md)

## Documentation References

- **Architecture**: `../docs/architecture/`
- **Implementation Plan**: `../docs/backend/`
- **API Contract**: `../docs/architecture/API_CONTRACT.md`
- **Deployment**: `../docs/deployment/`
- **LangGraph Deep Agents Guide**: `../docs/architecture/langchain-deep-agents-guide.md`
- **Professional Pivot Plan**: `../docs/PROFESSIONAL_PIVOT_PLAN.md`
- **Prompt Registry**: `src/rag_backend/agents/prompts/registry.py`
