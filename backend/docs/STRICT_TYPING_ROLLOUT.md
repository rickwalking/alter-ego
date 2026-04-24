# Strict Typing Rollout — Tracking Document

## Objective
Eliminate all `typing.Any` usage from the backend and enforce strict mypy rules for dead-code detection, unused imports/variables, and unnecessary type erasure.

---

## Phase 0 — Baseline & Cleanup ✅

### Done
- Updated `pyproject.toml`:
  - Added `show_error_codes = true` to `[tool.mypy]`.
  - Added `F401` (unused imports) and `F841` (unused variables) to `[tool.ruff.lint].select`.
  - Added `vulture>=2.14.0` to dev dependencies.
- Ran `ruff --select F401,F841 --fix src/` — removed 4 unused imports.
- Ran `vulture src/ --min-confidence 80` — fixed 2 unused parameters (`source_types` → `_source_types` in `ResearchTool` protocol + implementation).
- Replaced trivial `Any` usages with concrete types:
  - `api/app.py`: `_build_checkpointer(settings: Any, ...)` → `settings: Settings`
  - `carousel/nodes/content.py`: `extract_json(raw: str) -> Any` → `-> object`
  - `carousel_template.py`: All `dict[str, Any]` for slide data → `dict[str, object]`
  - `carousel/nodes/design.py`: `list[dict[str, Any]]` for slide_dicts → `list[dict[str, object]]`

---

## Phase 1 — Ban Explicit `Any` ✅

**Flag enabled:** `disallow_any_explicit = true`

### Changes Made

- Created `domain/types.py` with TypedDicts:
  - `SparseEmbedding` — Pinecone sparse vector format
  - `ImageResult` — per-slide image generation outcome
  - `PipelineEvent` — SSE event from `CarouselAgent.stream_pipeline`
  - `ChatEvent` — event from `RAGAgent.chat`
  - `StatsResponse` — vector store statistics
- Created `carousel/types.SlideDict` — dictionary shape for template renderers
- Updated **11 files** to replace explicit `Any` with concrete types:
  - `rag_agent.py`: `list[Any]` → `list[BaseTool]`, `AsyncIterator[dict[str, Any]]` → `AsyncIterator[ChatEvent]`
  - `carousel_agent.py`: `BaseCheckpointSaver[Any]` → `BaseCheckpointSaver[object]`, `AsyncIterator[dict[str, Any]]` → `AsyncIterator[PipelineEvent]`
  - `carousel/graph.py`: `-> Any` → `-> CompiledStateGraph`, all `dict[str, Any]` → `dict[str, object]`
  - `carousel/subagent.py`: `BaseCheckpointSaver[Any]` → `BaseCheckpointSaver[object]`, `dict[str, Any]` → `dict[str, object]`
  - `carousel/state.py`: `list[dict[str, Any]]` → `list[ImageResult]`
  - `domain/protocols.py`: `dict[str, Any]` → `SparseEmbedding` / `StatsResponse` / `ChatEvent` / `PipelineEvent`
  - `openai_embeddings.py`: `list[dict[str, Any]]` → `list[SparseEmbedding]`
  - `pinecone_store.py`: `dict[str, Any]` → `SparseEmbedding` / `StatsResponse`
  - `api/schemas.py`: `dict[str, Any]` → `dict[str, object]`
  - `rag_agent_tools.py`: `Callable[..., Awaitable[str]]` → `BaseTool`
  - `hybrid_retriever.py`: `dict[str, dict[str, Any]]` → internal `_DocScore` dataclass
- Added per-module mypy overrides for Pydantic model files where `Any` is unavoidable in base-class signatures:
  - `rag_backend.api.schemas`
  - `rag_backend.api.routes.auth`
  - `rag_backend.infrastructure.config.settings`

### Verification

| Check | Status |
|-------|--------|
| `grep -r 'Any' src/` (explicit) | ✅ Zero hits |
| `mypy src/ --disallow-any-explicit` | ✅ 0 explicit-any errors (47 Pydantic-base-class errors suppressed via per-module overrides) |

---

## Phase 2 — Ban `Any` in Generics ✅

**Flag enabled:** `disallow_any_generics = true`

**Flags disabled (pragmatic decision):**
- `disallow_any_expr = true` — disabled because it catches `Any` leaking from every untyped third-party library call (LangChain, LangGraph, Pinecone, SQLAlchemy, structlog, yaml, etc.). Fixing this would require `type: ignore` on nearly every line that touches an external library, producing noise without value.
- `disallow_any_decorated = true` — disabled for the same reason; untyped library decorators (e.g., `@tool`, `@app.get`, `@dataclass` from untyped packages) trigger this constantly.

### Changes Made

Fixed **8 `type-arg` errors** across 7 files by adding missing type parameters to generics:

| File | Before | After |
|------|--------|-------|
| `document_pipeline.py:113` | `-> dict` | `-> dict[str, object]` |
| `conversation_service.py:23` | `metadata: dict \| None` | `metadata: dict[str, object] \| None` |
| `conversation_service.py:94` | `sources: list[dict] \| None` | `sources: list[dict[str, object]] \| None` |
| `infrastructure/auth.py:41` | `-> dict \| None` | `-> dict[str, object] \| None` |
| `api/middleware/auth.py:15` | `-> dict` | `-> dict[str, str]` |
| `api/middleware/auth.py:51` | `-> dict \| None` | `-> dict[str, str] \| None` |
| `carousel/graph.py:114` | `-> CompiledStateGraph` | `-> CompiledStateGraph[PipelineState, object, object, object]` |
| `api/routes/documents.py:83` | `metadata: dict` | `metadata: dict[str, object]` |

### Verification

| Check | Status |
|-------|--------|
| `mypy src/ \| grep type-arg` | ✅ 0 hits |

---

## Phase 3 — Automation & Documentation (Final)

- [ ] Update CI / pre-commit to run `mypy src/` and `ruff check src/` as gates.
- [ ] Update `backend/CLAUDE.md` and `AGENTS.md`:
  - Document the "no `Any`" rule and the `type: ignore` justification requirement.
  - Document the decision tree: `Protocol` → `object` → `cast` → `type: ignore`.
- [ ] Add `make lint-strict` target (Makefile or justfile).

---

## Current State

| Check | Status |
|-------|--------|
| `ruff check --select F401,F841 src/` | ✅ Pass |
| `vulture src/ --min-confidence 80` | ✅ Pass |
| `mypy src/` | ⚠️ 268 pre-existing errors (all from untyped third-party libs + missing annotations) |
| `mypy src/ \| grep explicit-any` | ✅ 0 hits |
| `mypy src/ \| grep type-arg` | ✅ 0 hits |
| `grep -r ': Any\b' src/` | ✅ 0 hits |
