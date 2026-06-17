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
├── skills/           # AI agent skills
│   ├── developer-skill/  # SDD-driven implementation skill
│   ├── qa-agent/         # Multi-dimensional QA validation skill
│   └── ...               # Other project-specific skills
├── docker-compose.yml
└── CLAUDE.md         # You are here
```

## Universal Rules (Apply to All Sub-Projects)

### Code Quality
- **No magic strings** — Extract all string literals to named constants
- **No `any` / `Any` / `object` types** — Use explicit, specific types
- **Backend functions accept max 3 arguments** — Use Pydantic models for API/service boundary payloads and typed command/config objects for internal grouping
- **Early returns preferred** — Avoid nested `if` statements; use guard clauses
- **Max 400 lines per file** — Split large files into focused modules
- **Constants in dedicated files** — Each context/module gets its own `constants` file

### Testing
- **90%+ coverage required** — Focus on branch coverage, not just line coverage
- **Gherkin-first approach** — Write `.feature` files with scenarios before implementing tests
  - Cover happy paths, edge cases, and failures
  - Tests should reference Gherkin scenarios in comments
- **When a `.feature` file is required vs when unit tests suffice (AE-0153):**
  - **Required** — any **behavior-changing** feature or bugfix ticket (new/changed
    user-visible behavior, API contract, workflow, or business rule). Write
    `.feature` scenarios covering happy + edge + failure first.
  - **Unit tests suffice** — **pure refactors** (no public/observable behavior
    change) and **CI/config/tooling** tickets (a new gate, lint rule, script, or
    workflow). These substitute focused unit tests **plus** the gate's own
    seeded-violation test. To use this path, the ticket MUST document: (a) an
    explicit "no public/user-visible behavior change" assertion, (b) the
    seeded-violation test (for CI/config work), (c) the affected gates, and
    (d) reviewer/QA sign-off on the no-`.feature` classification.
  - **Tie-break** — if author and QA disagree on whether a ticket is
    behavior-changing, **default to requiring a `.feature`**; QA (the quality
    guardian) is the deciding authority.
- **Rule-fires regression test (mandatory for any static-analysis rule; AE-0180)** —
  any ticket that **adds or promotes** a static-analysis rule (ESLint, ruff, or a
  custom `scripts/` checker) MUST ship a test that proves the rule **FIRES on a
  seeded violation** (asserts a non-zero exit or `severity === 2`), not merely
  that the current tree passes. "Passes on the real tree" proves nothing about
  whether the rule catches its target. Exemplars:
  `frontend/src/scripts/use-client.test.ts`,
  `frontend/src/scripts/eslint-fetch-rule.test.ts`. See
  [`docs/guides/qa-checkpoints.md` → Rule-fires regression test](docs/guides/qa-checkpoints.md#rule-fires-regression-test-standard-ae-0180).
- **Test behavior, not implementation**
- **Mock external dependencies**
- **Mutation testing** — Weekly `mutmut` (backend) and Stryker (frontend) runs to validate assertion quality
  - Target: 70%+ mutation score on business logic
  - Disable `Regex` and `ObjectLiteral` mutators (high noise)
  - Run incrementally on PRs after 80%+ baseline established

### Documentation
- All documentation lives in `/docs/` with organized sub-folders
- CLAUDE.md files in sub-projects reference docs via progressive disclosure
- Keep README files concise; link to detailed docs
- **Architecture Decision Records (ADRs)** — Every architecturally significant decision requires an ADR in `docs/decisions/`
  - Use MADR 4.x format (Markdown Architectural Decision Records)
  - File naming: `NNNN-short-title.md` (e.g., `0002-use-langgraph-for-workflow-engine.md`)
  - Status lifecycle: `proposed` → `accepted` → `deprecated` (superseded by newer ADR)
  - Review ADRs annually; update status when decisions change

### Git & Commits
- Conventional commit messages
- One logical change per commit
- No secrets or API keys committed
- **Pre-commit hooks must run; `--no-verify` policy (AE-0168):** a normal
  `git commit` runs `.husky/pre-commit` (prettier/eslint via `lint-staged`) and
  `.husky/commit-msg` (commitlint). The hooks `cd frontend` and unset the git
  worktree env so they are reliable from the repo root AND inside a worktree.
  `core.hooksPath` is set to a **relative** `.husky` by `frontend` `prepare`
  (run `cd frontend && npm install` once after cloning).
  - **Do NOT use `git commit --no-verify` routinely** — it bypasses formatting
    and lets unformatted code reach the (still-blocking) `frontend:format` CI gate.
  - `--no-verify` is acceptable ONLY for: non-interactive automation/CI commits,
    or a documented hook-environment failure — and only when the equivalent gates
    (`bash scripts/ci/gates.sh frontend`) have been reproduced green by hand. State
    the reason when you use it.

## Sub-Project Rules

Each sub-project has its own `CLAUDE.md` and `AGENTS.md` with specific rules:

- **`backend/CLAUDE.md`** — Python/FastAPI rules (mypy strict, protocols, constants, LangGraph)
- **`frontend/CLAUDE.md`** — React/Next.js rules (i18n, component patterns, tests)

When working on a sub-project, **always read its local CLAUDE.md first**, then this root file for universal rules.

## Architecture Decision Records (ADRs)

All architecturally significant decisions are documented as ADRs in `docs/decisions/`:

- [ADR-001: Adopt MADR for ADRs](docs/decisions/0001-adopt-madr-for-adrs.md)
- [ADR-002: Use LangGraph for Workflow Engine](docs/decisions/0002-use-langgraph-for-workflow-engine.md)
- [ADR-003: Implement Persona-Driven AI Content](docs/decisions/0003-implement-persona-driven-ai-content.md)
- [ADR-004: Adopt Event-Driven Architecture](docs/decisions/0004-adopt-event-driven-architecture.md)
- [ADR-005: Adopt Mutation Testing](docs/decisions/0005-adopt-mutation-testing.md)
- [ADR-006: Use JSONB for Rich Content](docs/decisions/0006-use-jsonb-for-rich-content.md)
- [ADR-007: Consolidate Carousel Pipelines Under DeepAgents](docs/decisions/0007-consolidate-carousel-pipelines-under-deepagents.md)
- [ADR-008: Agentic Delivery Workflow](docs/decisions/0008-agentic-delivery-workflow.md)
- [ADR-009: Adopt Domain Modular Monolith](docs/decisions/0009-adopt-domain-modular-monolith.md)
- [ADR-010: Suspense-based data loading (Server Components + TanStack Query + React 19 use())](docs/decisions/0010-suspense-data-loading.md)

**ADR Lifecycle:** `proposed` → `accepted` → `deprecated` (superseded by newer ADR)
**Format:** MADR 4.x | **Naming:** `NNNN-short-title.md` | **Review:** Annually

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

## AI Orchestration Standards

### LangGraph Deep Agents
- Use **Deep Agents** for complex multi-step workflows (carousel, blog post)
- Use **raw LangGraph** for deterministic nodes (formatting, scoring)
- Use **Subagent pattern** for parallel tasks (research, drafting)
- Use **`interrupt()`** for all human approval gates
- **Never wrap `interrupt()` in bare `try/except`** — always re-raise `GraphInterrupt`
- Use **DeltaChannel** (LangGraph 1.2+) for append-only state to prevent O(N²) checkpoint growth
- Make side effects before `interrupt()` idempotent

### Model Selection Strategy
| Task | Recommended Model |
|------|------------------|
| Orchestrator / Complex reasoning | Claude Sonnet 4 |
| Research / Data extraction | GPT-4o-mini |
| Creative writing / Voice matching | Claude Sonnet 4 |
| Quality scoring / Deterministic | GPT-4o-mini |
| Image generation | DALL-E 3 / Stable Diffusion |

### Persona Engine
- All AI-generated content must pass through `PersonaAgent.enforce()`
- Voice match score must be >= 70 before human review
- Forbidden phrases are blockers, not suggestions
- Record all human corrections in feedback loop for persona improvement

## Prompt Management Standards

### Prompts Live in `.md` and `.yaml` Files — Never in `.py`
- **System prompts:** Stored as `.md` files in `backend/src/rag_backend/agents/prompts/{agent}/{version}/system.md`
- **Parameterized prompts:** Stored as `.yaml` files with Jinja2 templates in `backend/src/rag_backend/agents/prompts/{domain}/{version}/{name}.yaml`
- **Shared guidelines:** Stored in `backend/src/rag_backend/agents/prompts/_shared/`
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

### Prompt Versioning Rules
- **Never modify existing prompt files** — create a new version folder (`v1` → `v2`)
- **Keep old versions** for rollback and A/B testing
- **Document changes** in version folder README
- **Test prompt changes** in isolation before updating default version
- **Prompt files are hot-reloadable** in development (cached in production)

## Observability Standards (Langfuse)

### All LLM Calls Must Be Traced
- Every LLM invocation uses Langfuse `CallbackHandler` via `get_langfuse_handler()`
- Metadata includes: `project_id`, `phase`, `agent_name`, `user_id`
- Tags identify: workflow phase, agent type, content type

### Langfuse Configuration
```python
from rag_backend.monitoring_langfuse import get_langfuse_handler

# Pass to LangChain callbacks
llm = ChatOpenAI(callbacks=[get_langfuse_handler()])

# Or use propagate_attributes for groups of calls
with propagate_attributes(metadata={"project_id": project_id, "phase": "research"}):
    result = await chain.ainvoke(input, config={"callbacks": [get_langfuse_handler()]})
```

### Required Metadata for Traces
| Field | Description | Example |
|-------|-------------|---------|
| `project_id` | Carousel/blog project UUID | `"550e8400-e29b-41d4-a716-446655440000"` |
| `phase` | Workflow phase | `"research"`, `"content_drafting"`, `"image_generation"` |
| `agent_name` | Agent/subagent name | `"researcher"`, `"content_drafter"` |
| `user_id` | Human reviewer/creator | `"pedro-user-id"` |
| `content_type` | Type of content | `"carousel"`, `"blog_post"`, `"chat"` |

### Langfuse Monitoring Checklist
- [ ] Traces grouped by `project_id` for full workflow visibility
- [ ] Token usage tracked per phase for cost analysis
- [ ] Latency measured per agent for performance optimization
- [ ] Errors tagged with retry count and failure reason
- [ ] Human approval events linked to trace via metadata

## Workflow State Machine Rules
- Every workflow phase transition emits an event to Redis Streams
- Human approval gates use `interrupt()` with explicit timeout (default: 24h)
- Auto-reject after timeout; never leave workflows stuck
- State changes are idempotent — same event processed twice produces same result
- Workflow audit log must be queryable by project_id and date range

See `docs/architecture/` for detailed architecture documents.
See `docs/plans/frontend-legacy-removal.md` for v1.0 UI removal inventory and CI guards.
See `docs/decisions/` for Architecture Decision Records.
See `docs/architecture/langchain-deep-agents-guide.md` for agent implementation details.

## Agentic Delivery

Repo-backed tickets and board state live under `.agent/` (canonical memory; visual Kanban is optional). Work tiers **T0–T3** control how much pipeline to run — hotfixes skip planner/architect. See [agentic delivery overview](docs/plans/agentic-delivery-system.md) and [ADR-008](docs/decisions/0008-agentic-delivery-workflow.md).

```bash
uv run python scripts/agent_tasks/validate_all_tickets.py
uv run python scripts/agent_tasks/render_board.py
```

## Development Skills

This project provides AI agent skills for development and quality assurance:

### `/developer-skill`
**Purpose**: Implement task details from plans following SDD (Spec-Driven Development).
**When to use**: After a plan/task is created, invoke the Developer Skill to implement acceptance criteria incrementally.
**Standards**: Always reads `CLAUDE.md` and `AGENTS.md` first. Self-verifies via lint, type check, and tests.
**Location**: `skills/delivery/developer-skill/SKILL.md`

### `/qa-agent`
**Purpose**: Validate implementation quality across security, code quality, acceptance criteria, and completeness.
**When to use**: After the Developer Skill completes, invoke the QA Agent to run parallel validation subagents.
**Dimensions**: Security (OWASP Top 10:2025), code quality (ruff, mypy, complexity), mutation testing (mutmut/StrykerJS), acceptance criteria validation, and orphan/unfinished code detection.
**Location**: `skills/delivery/qa-agent/SKILL.md`
**Reference**: `docs/guides/qa-checkpoints.md` — Full QA checkpoint reference

### Delivery orchestration skills

| Skill | Purpose |
|-------|---------|
| `/orchestrator-skill` | Ticket status, WIP, handoffs |
| `/planner-skill` | Epic breakdown (T3) |
| `/architect-skill` | Plan, validate, research, skeptical review, bugfix design |
| `/ticket-writer-skill` | Create `.agent/tasks/` files |
| `/release-manager-skill` | PR/release prep (no auto-merge) |

### Developer → QA Workflow

1. User creates a plan/task with acceptance criteria
2. Invoke `/developer-skill` to implement (reads standards, follows SDD)
3. Developer reports completion with implemented criteria
4. Invoke `/qa-agent` to validate across all dimensions
5. QA produces consolidated report with PASS/FAIL/WARN per dimension
6. If issues found, return to step 2 for fixes (Dev→QA loop)
7. When QA passes, mark task as complete
