# AE-0075 — Checkpoint and lock_version inventory with serialization confirmation

Status: Review
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

- [x] `docs/architecture/checkpoint-inventory.md` exists and records the
      backend per environment, checkpoint/thread counts, capture date,
      and a per-live-workflow finish-cost estimate (phases remaining)
- [x] At least one sanitized checkpoint fixture exists under
      `backend/tests/fixtures/checkpoints/` and is loaded by a test
- [x] WHEN the fixture is deserialized in a test environment that imports
      no `rag_backend.agents` or `rag_backend.application` modules THE
      payload SHALL deserialize successfully, OR the report SHALL name
      every class-path-dependent entry
- [x] The report contains an explicit verdict line: `Serialization:
      PORTABLE` or `Serialization: CLASS-PATH-DEPENDENT`. **Escalation
      downgraded (2026-06-12 interview, migrate-in-place track):** a
      CLASS-PATH-DEPENDENT verdict no longer blocks Phase 2.5 — the
      recorded policy is finish-or-restart for in-flight workflows; the
      verdict instead determines whether restarts are required around
      package moves
- [x] The `lock_version` distribution for `carousel_projects` and
      `blog_posts` is recorded with row counts and query text
- [x] WHEN the verdict is CLASS-PATH-DEPENDENT THE epic AE-0070 Blockers
      section SHALL be updated and AE-0072 notified before its
      operating-context section is finalized
- [x] No fixture contains unsanitized user content (manual check recorded
      in Test Evidence)
- [x] WHEN no persisted checkpoint exists in any reachable store THE
      report SHALL record that fact and the fixture SHALL be produced
      from a documented dev workflow run with its provenance noted
- [x] The portability test enforces the no-project-imports condition
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

- [x] Security reviewed (fixture/report audit; PASS 100/100)
- [x] Code quality reviewed (ruff clean; scripts robust)
- [x] Acceptance criteria validated (all verified independently)
- [x] Edge cases tested (reproducibility, scanner blind spots)
- [x] Orphan/unfinished code checked (all artifacts accounted for)

## Progress Log

### 2026-06-12 00:00

Ticket created by planner.

### 2026-06-12 (development)

Implemented on docs/ae-0075-checkpoint-inventory. Checkpoints found in
dev sqlite store (not postgres); fixture captured from latest thread.

## Files Touched

- `docs/architecture/checkpoint-inventory.md` (new report)
- `backend/tests/fixtures/checkpoints/carousel_checkpoint.msgpack.bin` + `.meta.json` (new fixture)
- `backend/tests/features/checkpoint_fixture_portability.feature` (new)
- `backend/tests/unit/test_checkpoint_fixture_portability.py` (new, 3 tests)
- `.agent/reports/domain-modularization.options.md` (lock_version correction)

## Test Evidence

```bash
uv run pytest tests/unit/test_checkpoint_fixture_portability.py -q  # 3 passed
uv run ruff check tests/unit/test_checkpoint_fixture_portability.py # clean
```

Store: sqlite 6,918 checkpoints / 67,705 writes / 1,636 threads; postgres
has no checkpoint tables. Blob scan: 0 class-path markers anywhere.
Subprocess decode asserts no rag_backend in sys.modules (mechanical).
lock_version: carousel 1:23..18:1 (39 rows); blog_posts empty. Fixture
manually scanned: no emails/URLs/credentials (strings scan).
Verdict line in report: Serialization: PORTABLE.

## QA Report

`.agent/reports/wave1.qa.md` — wave-level external OpenCode QA
(CrofAI/kimi-k2.6): round 1 WARN 90/100 (A-), zero blockers, all ACs for
AE-0075 verified independently; round 2 confirmation after fix commit
716dba5: **PASS**. Status moved to Review per protocol.

## Decision Log

- Verdict PORTABLE → no escalation; finish-or-restart stands on
  convenience, not necessity.
- MAJOR CORRECTION surfaced: optimistic_lock_service.py EXISTS and is
  active (partial coverage, 3 route callers). The plan's "dead column"
  verification finding was wrong; plan annotated, Phase 2.5 scope
  reduced to coverage extension. AE-0072/AE-0073 consume this via the
  inventory report.
- Drain cost: ~23 workflows with any finish cost, each 1-2 approval
  clicks; full drain under an hour or restart-preferred for stale ones.

## Blockers

None.

## Final Summary

Inventory complete with PORTABLE verdict, sanitized fixture +
mechanical portability tests, lock_version distributions, live-workflow
finish costs, and one major plan correction (optimistic locking exists
with partial coverage). Both Phase 2.5 preconditions this ticket gates
are now evidence-backed.
