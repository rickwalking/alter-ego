# ADR-0015: Shared Deep Agents Harness (checkpointer / store / memory / middleware)

## Status

Accepted

> **Gated on ADR-0013.** The chat-agent portion of this harness MUST NOT wire a
> LangGraph checkpointer until ADR-0013 (chat-persistence source-of-truth) is
> Accepted. Per ADR-0013's Option A, chat agents receive **no** checkpointer at all;
> this ADR's builder must assert that default.

## Context

Today there is **no shared agent harness**. The checkpointer is centralized in the
composition root (`bootstrap/app_factory.py:133` `_build_checkpointer`, supporting
postgres/sqlite/memory/disabled with an `InMemorySaver` fallback at `:142/:158/:171`)
but it is consumed by **only** the carousel workflow
(`agents/carousel_workflow_engine.py:47` `graph.compile(checkpointer=…)`, keyed by
`thread_id=project_id` at `:55`). The two chat Deep Agents
(`agents/rag_agent.py`, `agents/alter_ego_agent.py`) run with no
checkpointer/store/middleware, manually replaying history from `message_repository`
(read `rag_agent.py:181` / `alter_ego_agent.py:130`; write `:198/:277/:315` and
`:147/:223/:261`). Interrupt parsing lives inline in the carousel engine.

`deepagents.create_deep_agent` (`backend/.venv/.../deepagents/graph.py:218`) accepts
`checkpointer`, `store`, `middleware`, `memory`, `interrupt_on` kwargs (verified;
`checkpointer: Checkpointer | None` at `:230`). LangGraph 1.2.5 ships
`SummarizationMiddleware` and `HumanInTheLoopMiddleware`. The harness's job is to
**preset and centralize** these so every agent composes from one surface, without
each agent re-inlining bootstrap concerns.

## Decision Drivers

- One composition surface for all agents (DRY; testable presets).
- Reuse the already-centralized `_build_checkpointer` rather than re-inventing it.
- Resist gold-plating — a full 8-module harness for two chat agents + one carousel
  graph risks over-abstraction; keep it to *relocate + 2 presets*.
- Honor ADR-0013: chat agents get no checkpointer; the carousel keeps its single
  writer.

## Decision

Create `backend/src/rag_backend/agents/harness/` as the single composition surface,
extracting today's scattered pieces and adding minimal presets:

- `checkpointer.py` — **relocate** `_build_checkpointer()` from `app_factory.py`;
  expose a `CheckpointerProvider` protocol + factory.
- `interrupts.py` — **relocate** interrupt parsing/merge helpers from the carousel
  engine.
- `store.py` — **new**, minimal: a `BaseStore` provider (Postgres/InMemory) for
  long-term memory.
- `memory.py` — **new**, minimal: load a per-agent `AGENTS.md` as `memory=`
  (registry-loadable), conversation-summarization config.
- `middleware.py` — **new**, minimal: `SummarizationMiddleware` +
  `HumanInTheLoopMiddleware` presets.
- `builder.py` / `config.py` — `build_deep_agent(config)` wrapping
  `create_deep_agent`; `DeepAgentConfig` carries model (incl. the ADR-0014 per-role
  model map), tools, subagents, system_prompt, memory, store, middleware. **The
  builder asserts chat-agent configs carry no checkpointer** (ADR-0013 guard), so a
  future edit cannot silently re-enable a chat checkpointer.

**Adoption:**

- **Carousel orchestrator** — keeps its raw-LangGraph graph but pulls the
  checkpointer + interrupt helpers from the harness instead of inlining them. Its
  single-writer checkpoint is unchanged.
- **Chat Deep Agents** — adopt the harness for `store` / `memory` / `middleware`
  (notably `SummarizationMiddleware` to cap window growth). **No checkpointer**
  (ADR-0013, Option A).

**Sequencing:** the non-chat pieces (relocating `_build_checkpointer`, interrupt
helpers, carousel-engine consumption) are **not** blocked by ADR-0013 and may ship
first. The chat-agent harness wiring is gated on ADR-0013 being Accepted, and even
then adds no checkpointer.

## Consequences

**Good:**

- One tested composition surface; bootstrap concerns leave `app_factory.py` and the
  carousel engine.
- Chat agents gain summarization/memory/store without a persistence change.
- The ADR-0013 guard is enforced in code (builder assertion), not just by convention.

**Bad / constraints:**

- A harness for two agents + one graph is borderline over-engineering — keep it to
  relocation + the two presets; do **not** build `agent_factory`/`BootstrapHarness`
  abstractions nobody consumes yet.
- Touches the composition root and both chat agents → moderate import churn.

## Related Decisions

- ADR-0013 (BLOCKER — chat persistence source-of-truth; the no-checkpointer rule).
- ADR-0014 (the per-role model map carried in `DeepAgentConfig`).
- ADR-007 (carousel stays raw-LangGraph deterministic nodes).
- ADR-009 (Clean Architecture; harness is orchestration, holds no infra logic).

## Open Questions (for human before proposed → accepted)

- Confirm the harness scope stays minimal (relocate + summarization + store/memory);
  reject any builder/factory abstraction without a second concrete consumer.

## Tags

#agents #harness #deepagents #langgraph #middleware #checkpointer
