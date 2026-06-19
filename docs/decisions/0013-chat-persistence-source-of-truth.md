# ADR-0013: Chat-Persistence Source-of-Truth (message_repository canonical; chat agents get no LangGraph checkpointer)

## Status

Proposed

> **Blocker.** This ADR gates Phase 3 (the Deep Agents harness) of the
> agent-architecture-restructure epic. The harness MUST NOT wire a LangGraph
> checkpointer onto either chat Deep Agent until this ADR is **accepted**. The
> sequence is **decide-then-build**, never build-then-decide.

## Context

The agent-layer restructure plan extracts a shared Deep Agents **harness**
(checkpointer / store / memory / middleware) so both chat agents and the carousel
workflow consume one composition surface
(`.agent/reports/agent-architecture-restructure.arch-plan.md` §5). A naive harness
would give the two chat Deep Agents a LangGraph `checkpointer=` keyed by
`thread_id=conversation_id`. An external skeptical pass
(`.agent/reports/agent-architecture.skeptical-corrections.md`) caught that this is
**not** additive: the chat agents are **already stateful** and a checkpointer would
create a *second* durable write path — the AE-0163 dual-write data-loss class.

### Verified current state (live code, cited)

**The two chat agents persist to Postgres and replay history from it each turn.**
The read/write lifecycle, per turn, is:

1. **Read history** from Postgres at turn start:
   - `agents/rag_agent.py:181` → `self._message_repository.get_by_conversation(ctx.conversation_id, limit=10)`
   - `agents/alter_ego_agent.py:130` → same call.
   - The result is rebuilt into LangChain `HumanMessage`/`AIMessage` objects
     (`rag_agent.py:185-190`, `alter_ego_agent.py:134-139`) and passed to the
     agent as `messages`. The agent itself holds **no** persistent state between
     turns — history is reconstructed from the DB on every invocation.
2. **Write the user message** (guarded by `ctx.persist_messages`):
   - `rag_agent.py:198`, `alter_ego_agent.py:147` → `message_repository.create(user_message)`.
3. **Write the assistant message** after generation (streaming and non-streaming
   paths both write):
   - `rag_agent.py:277` (streaming), `:315` (non-streaming)
   - `alter_ego_agent.py:223` (streaming), `:261` (non-streaming).

So `message_repository` is, today, the **sole** durable store and the **sole**
read source for chat history. There is no LangGraph checkpointer on either chat
agent (`rag_agent.py` / `alter_ego_agent.py` call `create_deep_agent(...)` with no
`checkpointer=`).

**`deepagents.create_deep_agent` DOES accept a `checkpointer=` kwarg.** Verified at
`backend/.venv/lib/python3.11/site-packages/deepagents/graph.py:230`:
`checkpointer: Checkpointer | None = None` (keyword-only; alongside `store`,
`middleware`, `memory`, `interrupt_on`). The pinned version is `deepagents>=0.5.3`.
So a checkpointer is *technically available* to the chat agents — the constraint is
**architectural (data integrity), not capability.**

**The carousel workflow is the only checkpointer consumer today.** The composition
root builds one checkpointer
(`bootstrap/app_factory.py:116` → `_build_checkpointer(...)`, defined at `:133`;
postgres/sqlite/memory/disabled with an `InMemorySaver` fallback at `:142`/`:158`/`:171`)
and it is consumed **only** by the carousel graph
(`agents/carousel_workflow_engine.py:47` → `graph.compile(checkpointer=checkpointer)`,
keyed by `thread_id=project_id` at `:55`). The carousel workflow has no
`message_repository`-style parallel writer — its checkpoint IS its state-of-truth.
Chat does not touch this checkpointer at all.

### Why a decision is required

If the harness wires a checkpointer onto the chat agents while the explicit
`message_repository.create(...)` writes remain, **both** paths persist the same
conversation independently → divergence the instant one path errors, is rolled
back, or is edited out-of-band. That is the exact AE-0163 failure class flagged in
project memory and in CLAUDE.md's dual-write prohibition.

## Decision Drivers

- **No dual-write, ever** (AE-0163 class; CLAUDE.md hard rule).
- **Auditability** — the API/UI read history from `message_repository` today; any
  canonical store must keep a queryable, single-writer read path.
- **Minimal blast radius** — chat is live in production (auto-deploys on `main`); a
  persistence migration is a prod-data operation, not a refactor.
- **Capability reality** — `create_deep_agent` supports `checkpointer=`, so the
  decision is about *whether we should*, not *whether we can*.
- **The carousel workflow already has a correct, single-writer checkpoint** and
  must keep it.

## Considered Options

### Option A — `message_repository` stays canonical; chat agents get NO checkpointer (RECOMMENDED)

The harness checkpointer serves **only** the stateful carousel workflow (which
already consumes it via `carousel_workflow_engine.py:47`). The chat Deep Agents keep
their DB-backed history (read at `rag_agent.py:181` / `alter_ego_agent.py:130`,
written at `:198/:277/:315` and `:147/:223/:261`). No second durable writer is
introduced. Long-context window growth — the *only* real motivation for a chat
checkpointer — is addressed instead by `SummarizationMiddleware` (a window-compression
concern, not a persistence concern), which needs no checkpointer.

- **Pros:**
  - **Zero dual-write risk** — exactly one durable writer for chat (`message_repository`).
  - **Zero migration / backfill** — no prod-data move; nothing to reconcile.
  - History stays auditable and queryable via the existing repository + API read
    path; no new read path for the UI.
  - Smallest harness surface — the harness still provides `store`/`memory`/`middleware`
    to chat (long-term memory, AGENTS.md, summarization) *without* the checkpointer.
  - The carousel workflow is untouched and keeps its single-writer checkpoint.
- **Cons:**
  - Manual history replay (`get_by_conversation` → rebuild messages) remains, rather
    than being delegated to LangGraph checkpoint replay. (Counter: it is simple,
    explicit, auditable, and already working.)
  - The chat agents do not benefit from LangGraph's interrupt/resume-from-checkpoint
    machinery — acceptable, because chat has no HITL interrupt gates (those live in
    the carousel workflow).

### Option B — Checkpointer becomes canonical and REPLACES the `message_repository.create` calls

Remove the explicit chat writes; history is reconstructed from the LangGraph
checkpoint. Requires: `create_deep_agent` to accept `checkpointer=` (it does,
graph.py:230); a **migration/backfill** of existing `message_repository` rows into
checkpoint state; and a **new read path** for the API/UI that currently reads
`message_repository.get_by_conversation` (every chat history endpoint + any analytics
on the messages table would have to read checkpoint blobs instead).

- **Pros:**
  - Single conceptual store; history replay handled by LangGraph.
  - Unifies chat with the carousel workflow's checkpoint model.
- **Cons:**
  - **Large, risky prod-data migration** on a live, auto-deploying surface.
  - The checkpoint is an **opaque serialized blob**, not a queryable relational
    table — the UI/API/analytics read path regresses badly; `message_repository`'s
    role as an auditable, queryable record is lost.
  - Rewrites the read path in both agents and every consumer of the messages table.
  - High effort for benefit that Option A's summarization middleware delivers
    without the migration.

### Option C — Checkpointer canonical for agent state; one-way async sync to `message_repository` for audit/API reads

The checkpoint is the single writer of agent loop state; a documented **one-way**
sync projects it into `message_repository` as a read replica (the repo is **never**
independently written by the agent loop). The API/UI keep reading
`message_repository` unchanged.

- **Pros:**
  - Preserves the queryable read path for the UI/API/analytics.
  - Single writer in principle (checkpoint), repo is derived — *not* a dual-write
    if the discipline holds.
- **Cons:**
  - **Requires deleting the existing `message_repository.create(...)` writes**
    (`rag_agent.py:198/277/315`, `alter_ego_agent.py:147/223/261`) and replacing
    them with a sync projector — any missed call site silently re-introduces the
    dual-write.
  - A sync pipeline is **new infrastructure** (failure modes, lag, replay, ordering)
    for chat, which has none today.
  - Still needs the backfill of Option B.
  - Over-engineered for a single-user product whose chat history is already simple
    and correct.

## Decision

**Adopt Option A.** `message_repository` remains the canonical, single-writer store
and read source for chat conversation history. The shared Deep Agents harness
(ADR-0015) provides a checkpointer **only** to the carousel workflow (which already
consumes it and has no parallel writer). The chat Deep Agents are **not** given a
LangGraph `checkpointer=`. Long-context window growth is handled by
`SummarizationMiddleware` from the harness, which is a window-management concern and
introduces no second durable store.

This is grounded in the `create_deep_agent` finding: the kwarg *is* available
(graph.py:230), so we are choosing **not** to use it for chat on data-integrity
grounds, not because we cannot. Because the capability exists, the harness builder
MUST make "no checkpointer on chat agents" an explicit, asserted default — not an
accident of omission — so a future change to the harness cannot silently re-enable
a chat checkpointer and re-introduce the dual-write.

**Explicit gate rule:** Phase 3 harness work (the chat-agent harness wiring in
particular) is **BLOCKED until this ADR is Accepted.** The harness's non-chat pieces
(relocating `_build_checkpointer`, interrupt helpers, carousel-engine consumption)
are not blocked by this ADR, but no chat-agent checkpointer may be wired under any
circumstance while Option A stands.

## Consequences

**Good:**

- Chat keeps exactly one durable writer (`message_repository`); the AE-0163
  dual-write class is structurally impossible for chat.
- No prod-data migration or backfill; nothing to reconcile on a live,
  auto-deploying surface.
- The UI/API/analytics read path (`get_by_conversation`) is unchanged.
- The carousel workflow's single-writer checkpoint is preserved as-is.
- Window growth is still solved (summarization middleware), decoupled from
  persistence.

**Bad / constraints:**

- The chat agents keep manual history replay (read-rebuild from Postgres) rather
  than LangGraph checkpoint replay. (Intended; it is simple and auditable.)
- The harness builder must **assert** chat agents receive no checkpointer (a guard
  + test), because the kwarg is available and a careless future edit could pass one.
- If a future need genuinely requires LangGraph interrupt/resume in chat, this ADR
  must be superseded by a new ADR that re-evaluates Option C (one-way sync) with a
  proper migration plan — it cannot be done ad hoc inside the harness.

## Related Decisions

- ADR-0015: Shared Deep Agents harness (consumes this decision; gated on it).
- ADR-009: Adopt Domain Modular Monolith (persistence ownership is significant).
- ADR-012: Production uses Alembic Migrations on Deploy (any future persistence
  migration, e.g. Option B/C, would require a migration under that ADR).
- Project memory: AE-0163 dual-write data-loss class; "No git add -A with
  uncommitted work" / prod auto-deploy hazard.

## Open Questions (for human before proposed → accepted)

- Confirm there is **no** roadmap requirement for LangGraph interrupt/resume in
  chat (HITL gates) that would force Option C. If chat will gain approval gates,
  re-weigh now rather than later.

## Tags

#agents #persistence #checkpointer #deepagents #data-integrity #blocker
