# AGENTS.md - Backend

## General Guidelines for AI Agents

This document provides general guidelines for AI agents working on the Python backend. For project-specific context, see `CLAUDE.md`.

---

## Core Principles

### 1. Type Safety First
- **mypy strict mode** — All code must pass `mypy --strict`
- **No explicit `Any` types** — `disallow_any_explicit = true`. Use `Protocol`, `TypedDict`, `object`, or `cast` instead.
- **No bare generics** — `disallow_any_generics = true`. Always parameterize `dict`, `list`, `Callable`, etc. (e.g., `dict[str, object]`, `list[int]`).
- **Use `Protocol` for interfaces** — Define contracts, not implementations
- **All functions have explicit return types** — No implicit `None` returns
- **Use `TypedDict` for structured dictionaries** — Never `dict[str, Any]`
- **Decision tree for dynamic data**: `Protocol` → `object` → `cast(T, value)` → `type: ignore[any]` (last resort, with justification comment)

### 2. No Magic Strings
- Extract all string literals to named constants
- Constants live in `constants.py` files per context
- Use `UPPER_SNAKE_CASE` for constant names

### 3. Clean Architecture
- **Domain layer** — Entities and Protocol interfaces only
- **Application layer** — Services and use cases
- **Infrastructure layer** — Implementations of protocols
- **API layer** — FastAPI routes, middleware, schemas

### 4. Testing is Non-Negotiable
- **90%+ branch coverage** — Focus on branches, not lines
- **Gherkin scenarios first** — Write `.feature` files before tests
- **Test behavior, not implementation**
- **Mock external dependencies**

---

## File Organization

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Modules | snake_case | `document_repository.py` |
| Classes | PascalCase | `PostgresDocumentRepository` |
| Functions | snake_case | `get_all_documents` |
| Constants | UPPER_SNAKE_CASE | `STATUS_PENDING` |
| Tests | test_ prefix | `test_create_document` |
| Features | .feature extension | `documents.feature` |

### Directory Structure

```
src/rag_backend/
├── api/
│   ├── routes/           # FastAPI route handlers
│   ├── middleware/       # ASGI middleware
│   ├── schemas.py        # Pydantic models (grouped by category)
│   ├── dependencies.py   # FastAPI dependencies
│   └── app.py            # Application factory
├── application/
│   ├── services/         # Business logic services
│   └── use_cases/        # Single-purpose use cases
├── domain/
│   ├── models.py         # Domain entities
│   ├── protocols/        # Protocol interfaces (by category)
│   └── exceptions.py     # Domain exceptions
├── infrastructure/
│   ├── database/         # SQLAlchemy repos and config
│   ├── external/         # External service clients
│   ├── retrieval/        # Search and retrieval
│   └── config/           # Settings and DI container
└── constants.py          # Global constants
```

---

## Code Patterns

### Early Returns (Guard Clauses)

```python
# Good
async def process_document(doc_id: str) -> Document:
    document = await self._repo.get_by_id(doc_id)
    if document is None:
        raise DocumentNotFoundError(doc_id)
    if document.status != DocumentStatus.PENDING:
        raise InvalidDocumentStatusError(document.status)
    return await self._pipeline.process(document)

# Bad
async def process_document(doc_id: str) -> Document:
    document = await self._repo.get_by_id(doc_id)
    if document is not None:
        if document.status == DocumentStatus.PENDING:
            return await self._pipeline.process(document)
        else:
            raise InvalidDocumentStatusError(document.status)
    else:
        raise DocumentNotFoundError(doc_id)
```

### Dictionary-Based Dispatch

```python
# Good — Complex branching replaced with dictionary dispatch
HANDLERS: dict[str, Callable[[str], Awaitable[Document]]] = {
    "pdf": lambda path: process_pdf(path),
    "txt": lambda path: process_text(path),
    "md": lambda path: process_markdown(path),
}

async def process_by_type(file_type: str, path: str) -> Document:
    handler = HANDLERS.get(file_type)
    if handler is None:
        raise UnsupportedFileTypeError(file_type)
    return await handler(path)
```

### Protocol-Based Interfaces

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class DocumentRepository(Protocol):
    async def create(self, document: Document) -> Document: ...
    async def get_by_id(self, doc_id: str) -> Document | None: ...
    async def get_all(self, status: str | None = None) -> list[Document]: ...
```

---

## Testing Guidelines

### Test Structure

```python
import pytest

class TestDocumentEndpoints:
    """Integration tests for document API endpoints."""

    @pytest.mark.asyncio
    async def test_create_document(self, client):
        """Given valid document data, when POST /api/documents, then returns created document."""
        payload = {"title": "Test", "content": "Content"}
        response = await client.post("/api/documents", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test"
```

### Gherkin-Style Comments

```python
# Feature: Document Management
# Scenario: Create document with valid data
#   Given a valid document payload
#   When POST /api/documents
#   Then returns 201 with created document
async def test_create_document_valid(self, client): ...

# Scenario: Create document with missing content
#   Given a document payload without content
#   When POST /api/documents
#   Then returns 422 validation error
async def test_create_document_missing_content(self, client): ...
```

---

## Code Review Checklist

Before submitting code:

- [ ] All tests pass
- [ ] mypy --strict passes with no errors
- [ ] ruff check passes with no warnings
- [ ] No explicit `Any` types (`disallow_any_explicit`)
- [ ] No bare generics (`disallow_any_generics`) — `dict`, `list`, `Callable` are parameterized
- [ ] No unused imports/variables (`ruff --select F401,F841`)
- [ ] No magic strings — all extracted to constants
- [ ] Functions have explicit return types
- [ ] Early returns used instead of nested ifs
- [ ] No files over 400 lines
- [ ] Tests cover all branches
- [ ] No secrets or API keys in code
- [ ] Documentation updated (if needed)

---

## Prompt Management

### Prompts Live in `.md` and `.yaml` Files — Never in `.py`
- **System prompts:** Stored as `.md` files in `src/rag_backend/agents/prompts/{agent}/{version}/system.md`
- **Parameterized prompts:** Stored as `.yaml` files with Jinja2 templates in `src/rag_backend/agents/prompts/{domain}/{version}/{name}.yaml`
- **Shared guidelines:** Stored in `src/rag_backend/agents/prompts/_shared/`
- **Loading:** Use `get_system_prompt()` or `render_prompt()` from `agents.prompts.registry`

### Prompt Registry Usage
```python
from rag_backend.agents.prompts.registry import get_system_prompt, render_prompt

# Load system prompt from .md file
system_prompt = get_system_prompt("rag", version="v1")

# Render parameterized prompt from .yaml with Jinja2
prompt_text, model_config = render_prompt(
    "carousel", "content_prompt",
    variables={"topic": "AI", "audience": "devs"},
    version="v1",
)
```

## Architecture Decision Records

See `../docs/decisions/` for all ADRs:
- [ADR-002: Use LangGraph for Workflow Engine](../docs/decisions/0002-use-langgraph-for-workflow-engine.md)
- [ADR-003: Implement Persona-Driven AI Content](../docs/decisions/0003-implement-persona-driven-ai-content.md)
- [ADR-005: Adopt Mutation Testing](../docs/decisions/0005-adopt-mutation-testing.md)
- [ADR-006: Use JSONB for Rich Content](../docs/decisions/0006-use-jsonb-for-rich-content.md)

## Observability (Langfuse)

### All LLM Calls Must Be Traced
- Every LLM invocation uses Langfuse `CallbackHandler` via `get_langfuse_handler()`
- Metadata includes: `project_id`, `phase`, `agent_name`, `user_id`

### Required Metadata for Traces
| Field | Description | Example |
|-------|-------------|---------|
| `project_id` | Project UUID | `"550e8400..."` |
| `phase` | Workflow phase | `"research"`, `"content_drafting"` |
| `agent_name` | Agent/subagent name | `"researcher"` |
| `user_id` | Human reviewer | `"pedro-user-id"` |

### Example
```python
from rag_backend.monitoring_langfuse import get_langfuse_handler

llm = ChatOpenAI(callbacks=[get_langfuse_handler()])
```

*These guidelines ensure consistency and quality across the backend codebase.*
