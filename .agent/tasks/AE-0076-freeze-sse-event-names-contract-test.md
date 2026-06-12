# AE-0076 — Freeze SSE event-name inventory and add CI contract test

Status: Ready
Tier: T2
Priority: Medium
Type: Feature
Area: Cross-cutting
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0076-sse-event-name-freeze
Kanban Card: TBD
Created: 2026-06-12
Updated: 2026-06-12

## Goal

SSE event names are recorded as a frozen inventory with a CI contract test
that fails if any name changes, closing the silent-failure gap the round-3
review identified.

## Problem

Backend and frontend each define SSE event names in their own constants
with no cross-check that the values match. The modularization will move
streaming routes into module adapters; a value drift would silently stop
the UI from updating. Verified locations (2026-06-12):

- Carousel workflow SSE names: `backend/src/rag_backend/application/`
  `services/carousel/editorial_workflow_sse_constants.py`
  (`SSE_EVENT_PHASE_CHANGE`, `SSE_EVENT_PROGRESS`,
  `SSE_EVENT_REVIEW_REQUIRED`, `SSE_EVENT_ERROR`, `SSE_EVENT_ARTIFACT`,
  `SSE_EVENT_KEEPALIVE`) — note: these live in the **application layer**,
  a fact the inventory must record for later module-ownership decisions.
- Chat SSE names: `backend/src/rag_backend/domain/constants/chat_stream.py`.
- Redis stream event types: `backend/src/rag_backend/domain/constants/`
  `workflow_events.py` (`EVENT_TYPE_*`, `STREAM_CONTENT_EVENTS`).
- Frontend: its own constants map `EDITORIAL_WORKFLOW_SSE_EVENTS`,
  defined in `frontend/src/constants/editorial-workflow.ts` and consumed
  by `frontend/src/features/create/hooks/use-editorial-workflow-sse.ts` —
  the frontend does **not** subscribe via raw literals; the gap is that
  nothing verifies its values equal the backend's.

## Scope

- Enumerate every SSE event name and Redis stream event type from the
  three backend constant modules above plus any inline literals found by
  search; reconcile with the frontend constants map.
- Record the inventory in `docs/architecture/sse-event-inventory.md` with
  the frozen-strings rule from the plan ("string-frozen for the entire
  migration"), naming the emitting module (and its layer) per event.
- Backend contract test: asserts the three constant modules' values match
  the inventory exactly (a change fails the test until the inventory is
  consciously updated — and the inventory states names are frozen until
  Phase 8).
- Frontend contract test: asserts every value in
  `EDITORIAL_WORKFLOW_SSE_EVENTS` (and any other frontend event-name
  constants found) equals the inventory value — a **constant-set
  comparison**, not a literal hunt.
- One committed source-of-truth artifact consumed by both test suites
  (location and format decided in implementation; must be committed and
  imported/read by both tests).
- Both tests run in the existing CI quality gates (no new workflow files).

## Non-Goals

- No event renames, payload changes, or new events.
- No OpenAPI/schema drift tooling (Phase 7 scope).
- No SSE transport changes.

## Acceptance Criteria

- [ ] `docs/architecture/sse-event-inventory.md` lists every SSE event
      name and workflow event type with its emitting module, the module's
      layer, and the frozen rule stated
- [ ] The inventory names all three backend constant modules
      (`editorial_workflow_sse_constants.py`, `chat_stream.py`,
      `workflow_events.py`) and the frontend
      `EDITORIAL_WORKFLOW_SSE_EVENTS` map as the verified sources
- [ ] WHEN any backend SSE/event-type constant value changes THE backend
      contract test SHALL fail with a message naming the changed constant
- [ ] WHEN a frontend event-name constant value differs from the inventory
      THE frontend contract test SHALL fail naming the constant
- [ ] The source-of-truth artifact is a single committed file consumed by
      both the backend and frontend contract tests
- [ ] `rg` search evidence in the ticket's Test Evidence shows zero inline
      event-name literals in backend route/service code outside the three
      constant modules, or each finding is added to the inventory
- [ ] Backend test runs under `uv run pytest` and frontend test under
      `npm run test` with no new CI workflow files
- [ ] Existing SSE behavior is byte-identical (no production code changes
      except, at most, replacing inline literals with existing constants)

## Gherkin Scenarios

```gherkin
Feature: SSE event names are frozen during the migration

  Scenario: Backend constant matches the frozen inventory
    Given the frozen SSE event-name inventory
    When the backend contract test compares constants to the inventory
    Then every constant value matches exactly

  Scenario: A renamed event is caught in CI
    Given a backend constant whose value differs from the inventory
    When the backend contract test runs
    Then the test fails and names the mismatched constant

  Scenario: Frontend constants match the inventory
    Given the frontend EDITORIAL_WORKFLOW_SSE_EVENTS constants map
    When the frontend contract test compares its values to the inventory
    Then every frontend constant value exists in the inventory

  Scenario: Drifted frontend constant is caught in CI
    Given a frontend event-name constant whose value differs from the inventory
    When the frontend contract test runs
    Then the test fails and names the mismatched constant
```

## Delta

### ADDED

- `docs/architecture/sse-event-inventory.md`
- Backend inventory contract test
- Frontend inventory contract test (+ shared inventory artifact)

### MODIFIED

- At most: inline event-name literals replaced with existing constants

### REMOVED

- None

## Affected Areas

- Backend: contract test; possible literal→constant swaps
- Frontend: contract test
- Database: none
- API: none (behavior unchanged)
- Tests: two new contract tests
- Docs: inventory document
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: Phases 4-5 streaming-slice work (rollout rule 9 diffs this
  inventory). Scope note (2026-06-12 interview): no external consumers
  exist, so this freeze protects exactly one client — the in-repo
  frontend; under migrate-in-place, a frozen name may be changed only by
  updating inventory + both constant sets + frontend in one PR
- Blocked by: none
- Related: AE-0070, AE-0074 (partial overlap:
  `domain/constants/workflow_events.py` only)

## Implementation Plan

1. Search backend for `SSE_EVENT_`, `EVENT_TYPE_`, and inline literals in
   streaming routes; build the inventory.
2. Search frontend for `addEventListener`/event-name literals in SSE
   hooks; reconcile.
3. Write both contract tests against a single source-of-truth artifact.

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
