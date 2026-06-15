# AE-0130 — Transactional outbox (additive) for release/workflow events — durable at-least-once relay

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0130-transactional-outbox
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Add a transactional outbox (additive): an outbox table written in the same transaction as the state change, + a relay that publishes to Redis at-least-once with idempotency. Runs ALONGSIDE the existing after-commit publish (keep current delivery working); identical event payloads. Fixes the durability gap (events lost if Redis publish fails post-commit).

## Problem

workflow_event_service publishes to Redis on after_commit; if the publish fails post-commit the event is lost (no durability/replay). Phase 6 adds a durable outbox additively so release/workflow events are at-least-once.

## Scope

- Add an outbox table (event_id, type, aggregate_id, payload, created_at, published_at, attempts) written in the SAME UoW transaction as the state change (transactional).
- Add a relay (worker/poller) that publishes unpublished outbox rows to the existing Redis stream at-least-once, marks published, idempotent (stable event_id; consumers dedupe).
- Keep the existing after-commit publish path working (additive — do not remove it); event payloads IDENTICAL to today.
- Idempotency: same event processed twice → same result; the relay is safe to re-run.

## Non-Goals

- No removal of the current after-commit publish (additive).
- No event-payload change.
- No consumer rewrite.

## Modularization Alignment (2026-06-15)

Phase 6 of the modularization plan (§Phase 6). **Behavior-preserving + additive-only** for the IN scope — blog/publish/distribution/calendar/board/analytics responses + the public carousel /blog stay byte-identical; the migration is ADDITIVE (add origin + backfill; NO column drop); the outbox is ADDITIVE (alongside the existing after-commit publish); NO renames. The auto-publish behavior cutover + the destructive embedded-column drop are DEFERRED (documented follow-up; the approval≠release contract is already split in AE-0111). Follow `docs/architecture/module-conventions.md` + the modules/editorial+presentation pattern; reuse the platform UoW, the QA-guardian gates, and the AE-0103/0112/0122 import-contract + ratchet pattern; compose via DI at the edge (no get_container in module code). publishing is invoked BY editorial/presentation via the facade (acyclic; publishing imports no editorial/presentation internals). Precondition: Phase 5 (PR #19) merged. The checkpoint-drain rule applies to any schema-modifying migration (Phase 6's is additive ⇒ no drain needed).

## Acceptance Criteria

- [ ] AN outbox table SHALL be written in the same transaction (UoW) as the state change (additive Alembic migration, reversible)
- [ ] A relay SHALL publish unpublished outbox rows to Redis at-least-once and mark them published, idempotently (stable event_id)
- [ ] THE existing after-commit publish path SHALL keep working (additive); event payloads SHALL be identical to today
- [ ] WHEN the relay re-runs THE same event SHALL not produce a different result (idempotent; at-least-once)
- [ ] WHEN gates.sh + mypy + lint-imports + pytest run THEY SHALL pass; the AE-0125 safety net green

## Gherkin Scenarios

```gherkin
Feature: Transactional outbox (representative)

  Scenario: event persisted in the state transaction
    When a release event is emitted
    Then an outbox row is committed atomically with the state change

  Scenario: relay is idempotent
    When the relay processes the same outbox row twice
    Then the event is delivered at-least-once with the same result
```

## Delta

### ADDED

- outbox table + additive migration; outbox relay; outbox writer in the UoW
- tests/unit + integration for the outbox + relay idempotency

### MODIFIED

- workflow_event_service / event emission to also write the outbox (additive)

### REMOVED

- None

## Affected Areas

- Backend: publishing module
- Frontend: none (Phase 7)
- Database: additive migration (origin+backfill; outbox table); NO destructive drop
- API: none yet
- Tests: contract/behavior tests
- Docs: references conventions
- Prompts/LLM: none
- Observability: outbox/event delivery
- Deployment: none

## Dependencies

- Blocks: AE-0132
- Blocked by: AE-0126
- Related: ADR-0004, AE-0123

## Implementation Plan

1. Add the outbox table (additive migration) + transactional writer.
2. Add the idempotent relay.
3. Tests for atomicity + at-least-once; safety net green.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 6 breakdown).

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
