# AE-0247 — Implement ADR-0013 chat-persistence resolution (no chat checkpointer; assert guard)

Status: Dev Complete
Tier: T2
Priority: High
Type: Feature
Area: backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-18
Updated: 2026-06-18

## Goal

Realize ADR-0013's Option A: `message_repository` stays the canonical chat-persistence
store, the chat Deep Agents get **no** LangGraph checkpointer, and a guard/assert makes
it impossible to silently wire one — eliminating the AE-0163 dual-write hazard before
the harness (AE-0248) lands.

## Problem

The harness work (RES-9) would naively give the two chat Deep Agents a LangGraph
`checkpointer=` keyed by `thread_id=conversation_id`. The skeptical pass proved the
chat agents are **already stateful**: they persist every message to
`message_repository` (`rag_agent.py:198,277,315`; `alter_ego_agent.py:147,223,261`) and
rebuild history from Postgres each turn (`rag_agent.py:181`, `alter_ego_agent.py:130`).
Adding a checkpointer creates a **second durable write path** — the exact AE-0163
dual-write data-loss class. ADR-0013 resolves this: `message_repository` is canonical
and the chat agents get **no** checkpointer (Option A). This ticket makes that decision
executable and self-guarding, so a future harness change cannot reintroduce the
dual-write.

Evidence: ADR-0013 (Proposed → must be Accepted); arch-plan §5.1/§5.3;
skeptical-corrections.md revision #1.

## Scope

- Confirm/keep `message_repository` as the sole chat-persistence writer for the two
  chat Deep Agents (`rag_agent.py`, `alter_ego_agent.py`).
- Add a guard/assertion (in the agent build path and/or the future harness builder)
  that **no chat checkpointer is wired** — fails loudly if one is.
- A build-time capability note: record whether `deepagents.create_deep_agent`
  (`graph.py:218`) accepts `checkpointer=` (informs AE-0248's integration approach).

## Non-Goals

- Do **not** extract the harness here (that is AE-0248, RES-9). This ticket only lands
  the source-of-truth resolution + guard that the harness then depends on.
- Do not touch the carousel workflow's checkpointer (it is single-writer, keyed by
  `thread_id=project_id`, and stays).
- Do not migrate chat history into a checkpoint or add a one-way sync — Option A is
  "no checkpointer", not a sync.

## Acceptance Criteria

- [x] **ADR-0013 is Accepted** (commit `73db1746` accepted ADRs 0013–0017 on this branch).
- [x] The two chat Deep Agents (`rag_agent`, `alter_ego_agent`) build `create_deep_agent`
      with **no** checkpointer; `message_repository` remains the single durable
      chat-persistence writer (unchanged).
- [x] `assert_no_chat_checkpointer` guard in `agents/chat_persistence_guard.py` is called
      by both chat-agent build paths; raises `ChatCheckpointerError` on any non-None
      checkpointer. Seeded-violation test proves it trips; a wiring test proves both
      builders route through the single guard.
- [x] **Capability finding:** `deepagents.create_deep_agent` **DOES** accept
      `checkpointer: Checkpointer | None = None` (`.venv/.../deepagents/graph.py:230`,
      passed through at `:621`). So AE-0248's harness can pass a checkpointer to the
      **carousel** agent via the kwarg, while the chat builders pass none (guarded).
- [x] backend `pytest` (263 agent tests + 4 guard tests) / `mypy` / `ruff` green.

## Gherkin Scenarios

> Behavior-changing (it governs the chat-persistence write path and adds a guard that
> can fail agent construction), so a `.feature` IS required — happy + edge + failure.

```gherkin
Feature: Chat agents have a single canonical persistence path

  Scenario: A chat turn writes only to the message repository
    Given a chat Deep Agent processes a user message
    When the turn completes
    Then the message is persisted to message_repository
    And no LangGraph checkpoint write occurs for that thread

  Scenario: Wiring a chat checkpointer is rejected
    Given the agent build path is asked to attach a checkpointer to a chat agent
    When the build runs
    Then the guard raises and agent construction fails loudly
```

## Delta

### ADDED

- A no-chat-checkpointer guard/assert + its seeded-violation test.
- A capability finding on `create_deep_agent(checkpointer=)` acceptance.

### MODIFIED

- The chat-agent build path (assert Option-A default).

### REMOVED

- None (the dual-write path is prevented from ever being added, not removed).

## Affected Areas

- Backend: `agents/rag_agent.py`, `agents/alter_ego_agent.py`, the agent-build/harness
  guard.
- Frontend: none.
- Database: none (canonical store unchanged — `message_repository`).
- API: none.
- Tests: guard seeded-violation test + persistence-path `.feature`.
- Docs: ADR-0013 status flip; capability finding note.
- Prompts/LLM: none.
- Observability: none.
- Deployment: none (no new write path; avoids a data-loss class).

## Dependencies

- Provisional epic id: **RES-9a** (Phase 3 — source-of-truth resolution).
- Gating ADR: **ADR-0013 (chat-persistence source-of-truth) — MUST be Accepted** before
  this lands. This is the hard BLOCKER for Phase 3.
- Blocked by: ADR-0013 acceptance.
- Blocks: **AE-0248 (RES-9, harness)** — the harness MUST NOT wire a chat checkpointer
  until this resolution + guard exist.
- Related: AE-0163 (dual-write data-loss class, project memory).

## Implementation Plan

1. Confirm ADR-0013 Accepted; record Option A (message_repository canonical, no chat
   checkpointer).
2. Add the guard/assert in the agent-build path; add the seeded-violation test.
3. Run the build-time `create_deep_agent(checkpointer=)` capability check; document the
   finding for AE-0248.
4. Run gates.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (guard trips on seeded checkpointer; single-writer confirmed)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-18 21:30

Created from the agent-architecture-restructure epic (RES-9a). Gated on ADR-0013
acceptance; prevents the AE-0163 dual-write class before the harness lands.

## Files Touched

### ADDED
- `backend/src/rag_backend/agents/chat_persistence_guard.py` — `assert_no_chat_checkpointer`
  + `ChatCheckpointerError`.
- `backend/tests/unit/agents/test_chat_persistence_guard.py` — seeded violation + wiring.
- `backend/tests/features/chat_persistence.feature` — behavior scenarios.

### MODIFIED
- `agents/rag_agent.py`, `agents/alter_ego_agent.py` — call `assert_no_chat_checkpointer(None)`
  immediately before `create_deep_agent` (which is called without a checkpointer).

## Test Evidence

```
$ uv run pytest tests/unit/agents/test_chat_persistence_guard.py -q   # 4 passed
$ uv run pytest tests/unit/agents/ -q                                  # 263 passed
$ cd src && uv run mypy <guard+chat agents> --explicit-package-bases   # Success
$ uv run ruff check <guard+chat agents+test>                           # All checks passed!
```

Note: the airtight single-chokepoint enforcement lands with the shared harness
builder (AE-0248, deferred) which will route chat-agent construction through this
same guard; for now the guard is invoked directly by both chat builders.

## QA Report

Pending.

## Decision Log

- **Option A (no chat checkpointer) per ADR-0013.** The chat agents are already
  stateful via `message_repository`; a checkpointer = a second write path = the AE-0163
  dual-write trap. The guard makes the single-writer invariant enforceable so the
  harness cannot reintroduce it.
- **Decide-then-build sequencing.** ADR-0013 must be Accepted before this ticket lands,
  and this ticket must land before the harness wires anything.

## Test Classification (CLAUDE.md AE-0153 / AE-0180)

- **Behavior-changing** — it governs the chat-persistence write path and adds a guard
  that can fail agent construction. **`.feature` REQUIRED** (happy: single write path;
  failure: guard rejects a wired checkpointer).
- The guard is enforced by a seeded-violation test (the guard trips), complementing the
  `.feature` behavior scenarios.
- **Affected gates:** backend `pytest`/`mypy`/`ruff`.

## Blockers

- **ADR-0013 must be Accepted** before this ticket can be marked done.

## Final Summary

Pending.
