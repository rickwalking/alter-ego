# AE-0106 — Carousel workflow Gherkin safety net + API/SSE byte-identical snapshots

Status: Ready
Tier: T2
Priority: High
Type: Tests
Area: Tests
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: test/ae-0106-carousel-workflow-safety-net
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Build the byte-identical safety net for the carousel WORKFLOW slice before any refactor: capture committed response snapshots for workflow start/state/resume + an SSE-stream snapshot (deterministic mock workflow/agent), so AE-0107/0110/0111 can diff to zero. Build on AE-0044's existing response golden snapshot.

## Problem

Phase 4 moves workflow start/state/resume + the carousel_projects writers behind editorial handlers + an ACL; without an enforceable byte-identical baseline the refactor could silently change the workflow API, SSE framing, or checkpoint behavior.

## Scope

- Audit/extend the carousel workflow Gherkin (start/state/resume, interrupt/resume gates, optimistic-lock concurrent-resume) and back each scenario with an executing test.
- Capture committed response snapshots for GET workflow/state, POST workflow/start, POST workflow/resume — deterministic fields only; normalize volatile (timestamps/uuids) with a diff helper.
- Capture an SSE-stream snapshot for GET workflow/stream USING A DETERMINISTIC MOCK workflow/agent: assert event TYPES in order + `id:`/`data:` framing FORMAT + keep-alive + Last-Event-ID; ignore keep-alive interleaving (do NOT byte-diff live LLM/phase content).
- Pin environment-sensitive settings (e.g. DEBUG) in the test fixture so snapshots are deterministic across local + CI (lesson from AE-0097).

## Non-Goals

- No production code change.
- No new workflow behavior.
- No presentation/CRUD snapshots (Phase 5).

## Modularization Alignment (2026-06-15)

Phase 4 of the modularization plan (§Phase 4). **Behavior-preserving** — the carousel workflow API + SSE event names/framing/keep-alive/`Last-Event-ID`, artifact URLs, response schemas, LangGraph checkpoint identifiers + schemas, and `lock_version` optimistic-lock semantics stay byte-identical; NO renames (later phases). Follow `docs/architecture/module-conventions.md` + `modules/_template`; reuse the `platform/database` UoW, the QA-guardian gates, and the AE-0103 import-contract + baseline-ratchet pattern; compose via DI at the edge (no get_container in module code). `api/middleware/auth.py`, `infrastructure/auth.py`, and `api/dependencies/resource_access.py` stay at root (shared). Precondition: Phase 3 (PR #17) merged.

## Acceptance Criteria

- [ ] THE carousel workflow Gherkin SHALL cover start/state/resume, interrupt→resume gates, and concurrent-resume optimistic-lock behavior, each backed by an executing test
- [ ] THE committed workflow snapshots (state/start/resume) SHALL be true byte-identical baselines with a diff helper, volatile fields normalized deterministically
- [ ] THE SSE workflow-stream snapshot SHALL be captured via a DETERMINISTIC mock and assert event TYPES in order + `id:`/`data:` framing + keep-alive + Last-Event-ID (NOT a raw byte diff of phase/LLM content) — falsifiable by a reordered/renamed event
- [ ] THE test fixture SHALL pin environment-sensitive settings so snapshots are identical local vs CI
- [ ] THE workflow state snapshots SHALL include artifact URL fields (pdf/blog/design/image paths) as byte-identical baselines
- [ ] WHEN `uv run pytest` runs THE safety-net suite SHALL pass with NO production code modified (green baseline recorded)

## Gherkin Scenarios

```gherkin
Feature: Carousel workflow safety net (representative)

  Scenario: workflow state response unchanged
    Given a carousel project mid-workflow
    When GET /api/carousels/{id}/workflow/state runs
    Then the response matches the committed snapshot (volatile fields normalized)

  Scenario: workflow stream emits the same SSE event sequence
    Given a deterministic mock workflow
    When GET /api/carousels/{id}/workflow/stream runs
    Then the SSE event types/framing/keep-alive/Last-Event-ID match the snapshot
```

## Delta

### ADDED

- tests/integration/test_carousel_workflow_safety_net.py
- tests/snapshots/editorial/* + diff helper
- workflow Gherkin scenarios

### MODIFIED

- tests/features/*carousel*workflow*.feature (audit/extend)

### REMOVED

- None

## Affected Areas

- Backend: none
- Frontend: none
- Database: none (additive-only if any; no schema migration planned)
- API: none
- Tests: safety net + snapshots
- Docs: references conventions
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0107, AE-0110, AE-0111
- Blocked by: None
- Related: AE-0044, AE-0097, AE-0104

## Implementation Plan

1. Audit existing carousel workflow tests + AE-0044 golden snapshot.
2. Capture state/start/resume + SSE (mock) snapshots; pin DEBUG.
3. Record green baseline; no src/ change.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 4 breakdown).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
