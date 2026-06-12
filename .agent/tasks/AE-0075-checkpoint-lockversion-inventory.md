# AE-0075 — Checkpoint and lock_version inventory with serialization confirmation

Status: Ready
Tier: T2
Priority: High
Type: Research
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: docs/ae-0075-checkpoint-inventory
Kanban Card: TBD
Created: 2026-06-12
Updated: 2026-06-12

## Goal

Produce the evidence inventory that gates Phase 2.5: which checkpoint
backends hold live workflow state, whether checkpoint payloads are
portable or class-path-dependent, and the `lock_version` value
distribution.

## Problem

The plan's escalation rule blocks Phase 2.5 if checkpoint payloads prove
pickled (package renames would invalidate every persisted checkpoint).
Preliminary signal is good (`CarouselWorkflowState` is a `TypedDict`, no
custom serde configured, so LangGraph's default `JsonPlusSerializer`
applies) but only a real captured checkpoint confirms it. The ADR-0009
operating-context statement (AE-0072) also needs the live checkpoint count.

## Scope

- Inventory the configured checkpoint backend per environment
  (`settings.carousel_checkpoint_backend`: postgres/sqlite/memory/disabled)
  and count persisted checkpoints/threads in each reachable store.
- For each live (resumable) workflow found, record an owner-estimated
  **finish cost** (phases remaining, approvals pending) — this feeds the
  drain-before-migrate step in Phase 4+ (finish vs restart decision per
  workflow; round-4 review).
- Capture at least one real (sanitized) checkpoint produced by the current
  carousel workflow; commit it as a fixture under
  `backend/tests/fixtures/checkpoints/`.
- Determine the serialization format of the captured payload: confirm
  every stored value deserializes without importing project classes
  (portable) or identify class-path-dependent entries (pickled).
- Run and record the `lock_version` distribution:
  `SELECT lock_version, COUNT(*) FROM carousel_projects GROUP BY 1` (and
  the same for `blog_posts`).
- Publish `docs/architecture/checkpoint-inventory.md` with all findings
  and the explicit go/no-go statement for Phase 2.5 serialization risk.

## Non-Goals

- No checkpoint migration tooling (only triggered if the escalation fires).
- No workflow state versioning implementation (Phase 2.5+).
- No production credentials in fixtures — sanitize all user content.

## Acceptance Criteria

- [ ] `docs/architecture/checkpoint-inventory.md` exists and records the
      backend per environment, checkpoint/thread counts, capture date,
      and a per-live-workflow finish-cost estimate (phases remaining)
- [ ] At least one sanitized checkpoint fixture exists under
      `backend/tests/fixtures/checkpoints/` and is loaded by a test
- [ ] WHEN the fixture is deserialized in a test environment that imports
      no `rag_backend.agents` or `rag_backend.application` modules THE
      payload SHALL deserialize successfully, OR the report SHALL name
      every class-path-dependent entry
- [ ] The report contains an explicit verdict line: `Serialization:
      PORTABLE` or `Serialization: CLASS-PATH-DEPENDENT`. **Escalation
      downgraded (2026-06-12 interview, migrate-in-place track):** a
      CLASS-PATH-DEPENDENT verdict no longer blocks Phase 2.5 — the
      recorded policy is finish-or-restart for in-flight workflows; the
      verdict instead determines whether restarts are required around
      package moves
- [ ] The `lock_version` distribution for `carousel_projects` and
      `blog_posts` is recorded with row counts and query text
- [ ] WHEN the verdict is CLASS-PATH-DEPENDENT THE epic AE-0070 Blockers
      section SHALL be updated and AE-0072 notified before its
      operating-context section is finalized
- [ ] No fixture contains unsanitized user content (manual check recorded
      in Test Evidence)
- [ ] WHEN no persisted checkpoint exists in any reachable store THE
      report SHALL record that fact and the fixture SHALL be produced
      from a documented dev workflow run with its provenance noted
- [ ] The portability test enforces the no-project-imports condition
      mechanically (subprocess with a restricted environment or an
      import-hook assertion), not by convention

## Gherkin Scenarios

```gherkin
Feature: Checkpoint fixture portability

  Scenario: Captured checkpoint deserializes without project imports
    Given a sanitized checkpoint fixture captured from the carousel workflow
    When the fixture is deserialized using only LangGraph's default serializer
    Then deserialization succeeds
    And no project-specific class import is required

  Scenario: Class-path-dependent payload is detected and reported
    Given a checkpoint fixture containing a non-primitive serialized value
    When the portability test runs
    Then the test fails with the offending key path
    And the inventory report records the CLASS-PATH-DEPENDENT verdict
```

## Delta

### ADDED

- `docs/architecture/checkpoint-inventory.md`
- `backend/tests/fixtures/checkpoints/` fixture + portability test

### MODIFIED

- None

### REMOVED

- None

## Affected Areas

- Backend: read-only inspection + one new test module
- Frontend: none
- Database: read-only queries
- API: none
- Tests: new portability test
- Docs: inventory report
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0072 (operating-context statement), Phase 2.5 start
- Blocked by: none
- Related: AE-0070, AE-0073

## Implementation Plan

1. Read checkpointer wiring in `api/app.py`; enumerate environments.
2. Capture and sanitize a checkpoint; write the portability test.
3. Run distribution queries; write the report with the verdict line.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-12 00:00

Ticket created by planner.

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
