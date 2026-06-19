# AE-0248 — Extract shared Deep Agents harness (checkpointer/store/memory/middleware)

Status: In Development
Tier: T3
Priority: High
Type: Refactor
Area: backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-18
Updated: 2026-06-18

## Goal

Extract a shared `agents/harness/` package (checkpointer + store + memory + middleware,
including `SummarizationMiddleware` + interrupt helpers) so both chat Deep Agents and
the carousel orchestrator consume one composition surface — carousel keeps its
single-writer checkpoint, chat agents get **no** checkpointer (per ADR-0013/AE-0247).

## Problem

There is **no shared agent harness** today. The checkpointer is centralized in
`bootstrap/app_factory.py:133` (`_build_checkpointer`) but consumed only by the carousel
workflow (`carousel_workflow_engine.py:47`, keyed `thread_id=project_id`). The chat
Deep Agents (`rag_agent.py`, `alter_ego_agent.py`) run with no checkpointer/store/
middleware, manually replaying history — so long chats grow unbounded into the model
window (no `SummarizationMiddleware`), and interrupt parsing is inlined in the carousel
engine. ADR-0015 extracts a single composition surface; ADR-0013 (via AE-0247)
mandates that chat agents receive **no** checkpointer, so the harness must default to —
and assert — that.

Evidence: arch-plan §5.1/§5.2 (harness module layout) + §5.3 (gate); ADR-0015
(Proposed, gated on ADR-0013); ADR-0013/AE-0247.

## Scope

- Create `backend/src/rag_backend/agents/harness/`:
  `checkpointer.py` (move `_build_checkpointer` + a `CheckpointerProvider` Protocol),
  `store.py` (BaseStore provider), `memory.py` (per-agent `AGENTS.md` memory loading +
  summarization config), `middleware.py` (`SummarizationMiddleware` +
  `HumanInTheLoopMiddleware` presets + a custom `AgentMiddleware` base),
  `interrupts.py` (move interrupt parsing/merge helpers from the engine),
  `builder.py` (`build_deep_agent(config)`), `config.py` (`DeepAgentConfig`).
- Carousel orchestrator + both chat Deep Agents adopt the harness.
- Carousel keeps its existing single-writer checkpoint (pulled from the harness instead
  of inlined).

## Non-Goals

- Do **not** wire a chat-agent checkpointer — chat agents get none (ADR-0013 Option A,
  enforced by the AE-0247 guard). Adding `SummarizationMiddleware` is allowed; a chat
  checkpointer is not.
- Do not over-build: no `agent_factory`/`BootstrapHarness` abstractions nobody consumes
  (arch-plan §12 gold-plating warning). Keep the harness minimal (mostly relocation +
  2 presets).
- Do not change carousel topology or interrupt semantics — relocate the helpers, keep
  behavior.
- Do not introduce subagent taxonomy here (AE-0249) or façade packages (AE-0250).

## Acceptance Criteria

- [ ] `agents/harness/` exists with the modules above and a public `__init__` API;
      `_build_checkpointer` + interrupt helpers are **moved** there (not duplicated).
- [ ] The carousel orchestrator consumes the harness checkpointer + interrupt helpers;
      its single-writer checkpoint (`thread_id=project_id`) behavior is unchanged
      (regression test).
- [ ] Both chat Deep Agents are built via the harness builder with **no** checkpointer;
      the AE-0247 guard still holds (a test asserts no chat checkpoint write occurs).
- [ ] `SummarizationMiddleware` is available as a harness preset and wired to the chat
      agents (caps window growth) without altering their `message_repository`
      persistence.
- [ ] `build_deep_agent(config)` integrates `create_deep_agent` per the AE-0247
      capability finding (kwarg or `.compile(checkpointer=…)` fallback for carousel).
- [ ] Backend `pytest`/`mypy`/`ruff` green; carousel interrupt/HITL regression green.

## Gherkin Scenarios

> Behavior-changing (it adds summarization middleware to chat agents and re-routes the
> carousel checkpoint/interrupt path), so a `.feature` IS required — happy + edge +
> failure.

```gherkin
Feature: A shared harness composes all agents with the correct persistence defaults

  Scenario: Carousel keeps its single-writer checkpoint via the harness
    Given the carousel orchestrator is built through the harness
    When a workflow runs and hits an interrupt
    Then the checkpoint is written once per project thread
    And resume behavior is identical to before the extraction

  Scenario: Chat agents get summarization but no checkpointer
    Given a chat Deep Agent is built via the harness builder
    When a long conversation exceeds the summarization threshold
    Then history is summarized by the middleware
    And no LangGraph checkpoint is written for the chat thread

  Scenario: Wiring a chat checkpointer through the harness is rejected
    Given a DeepAgentConfig requests a checkpointer for a chat agent
    When build_deep_agent runs
    Then the AE-0247 guard raises and the build fails
```

## Delta

### ADDED

- `agents/harness/` package (8 modules per arch-plan §5.2) + tests.
- `SummarizationMiddleware` preset wired to the chat agents.

### MODIFIED

- Carousel orchestrator + both chat Deep Agents adopt the harness; interrupt helpers
  move out of `carousel_workflow_engine.py`; `_build_checkpointer` moves out of
  `app_factory.py`.

### REMOVED

- Inlined interrupt parsing in the carousel engine; the `_build_checkpointer` body in
  `app_factory.py` (relocated).

## Affected Areas

- Backend: `agents/harness/*`, `rag_agent.py`, `alter_ego_agent.py`,
  `carousel_workflow_engine.py`, `bootstrap/app_factory.py`.
- Frontend: none.
- Database: none (chat persistence stays `message_repository`).
- API: none.
- Tests: harness unit tests + carousel interrupt regression + chat no-checkpoint test.
- Docs: ADR-0015 status; harness README.
- Prompts/LLM: none (memory loading is per-agent `AGENTS.md`, wired in AE-0250).
- Observability: none new.
- Deployment: touches `bootstrap` composition root — exercise startup validation.

## Dependencies

- Provisional epic id: **RES-9** (Phase 3).
- Gating ADR: **ADR-0015 (shared harness) — gated on ADR-0013**. Both must be Accepted
  for the chat-agent portion.
- Blocked by: **AE-0247 (RES-9a)** — the source-of-truth resolution + no-chat-
  checkpointer guard + the `create_deep_agent` capability finding.
- Blocks: **AE-0249 (RES-10)** and **AE-0251 (RES-12)** — they consume the harness;
  **AE-0250 (RES-11)** wires per-agent `memory=` through it.
- Related: AE-0163 (dual-write), the carousel single-writer checkpoint.

## Implementation Plan

1. Scaffold `agents/harness/` (config, builder, checkpointer, store, memory,
   middleware, interrupts) — relocate `_build_checkpointer` + interrupt helpers.
2. Adopt the harness in the carousel orchestrator first (unblocked, no persistence
   change); regression-test interrupts/resume.
3. Build the chat agents via the harness with `SummarizationMiddleware` and **no**
   checkpointer; assert the AE-0247 guard.
4. Wire `build_deep_agent` to `create_deep_agent` per the capability finding; run gates.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (carousel resume parity; chat summarization; guard rejects checkpointer)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-18 21:30

Created from the agent-architecture-restructure epic (RES-9). T3 — touches the
composition root + both agents; the chat portion is gated on ADR-0013/AE-0247.

### 2026-06-19 (increment 3)

Final increment: added `config.py`/`middleware.py`/`store.py`/`memory.py`/`builder.py`
and wired both chat agents through `build_deep_agent` with `SummarizationMiddleware`
(no checkpointer — guard routed via the builder). Gates reproduced green (see Test
Evidence); `lint-imports` holds at 22 kept / 0 broken; AE-0247 guard test passes.

## Files Touched

Increment 3 (final):
- ADDED `agents/harness/config.py` (`DeepAgentConfig`, `AGENT_KIND_*`),
  `middleware.py` (summarization + HITL presets), `store.py` (`BaseStore` provider),
  `memory.py` (`resolve_memory_paths`), `builder.py` (`build_deep_agent`).
- MODIFIED `agents/harness/__init__.py` (public API), `agents/rag_agent.py` +
  `agents/alter_ego_agent.py` (build via harness + SummarizationMiddleware, no checkpointer).
- ADDED `tests/features/agent_harness.feature`, `tests/unit/agents/test_harness_builder.py`.
- MODIFIED `tests/unit/agents/test_chat_persistence_guard.py` (routing assertion now
  targets the harness builder, which centralizes the guard call).

## Test Evidence

- `ruff check src/ tests/` → All checks passed.
- `ruff format --check` (changed files) → all formatted.
- `mypy rag_backend/ + new test --explicit-package-bases` → Success, 0 issues (513 files).
- `lint-imports` → 22 kept, 0 broken (no new agents→application edge).
- `pytest tests/unit/agents tests/unit/bootstrap tests/integration/carousel_consolidation`
  → 348 passed (incl. AE-0247 guard test + new harness builder tests).
- `check-integrity.sh backend` → 0 blockers, 0 warnings.

## QA Report

Pending.

## Decision Log

- **Split the unblocked from the gated.** Relocating `_build_checkpointer` + interrupt
  helpers and having the carousel engine consume the harness is unblocked; only the
  chat-agent checkpointer wiring waits — and per ADR-0013 it is **never** wired
  (arch-plan §12). This keeps the harness from being held hostage by the ADR while
  honoring the no-dual-write rule.
- **Keep it minimal.** Two presets (summarization, store) + relocation; resist building
  abstractions nobody consumes (arch-plan §12 gold-plating risk).

## Test Classification (CLAUDE.md AE-0153 / AE-0180)

- **Behavior-changing** — adds summarization to chat agents and re-routes the carousel
  checkpoint/interrupt path; `SummarizationMiddleware` observably alters long-chat
  context. **`.feature` REQUIRED** (carousel resume parity; chat summarization; guard
  rejection).
- Not a pure refactor despite the "Refactor" type: middleware changes observable model
  context, so the AE-0153 exemption does NOT apply.
- **Affected gates:** backend `pytest`/`mypy`/`ruff` + startup validation.

## Blockers

- **ADR-0013 + ADR-0015 must be Accepted**, and **AE-0247** must be merged, before the
  chat-agent portion lands.

## Final Summary

Pending.
