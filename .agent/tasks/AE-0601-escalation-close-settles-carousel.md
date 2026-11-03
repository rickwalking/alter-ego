# AE-0601 — An abandoned escalation that closes also settles its carousel

Status: Dev Complete
Tier: T2
Priority: Low
Type: Bugfix
Area: Backend, autopilot recovery
Owner: Pedro
Agent Lane: developer → qa → release
Branch: fix/ae-0601-escalation-close-settles-carousel
Kanban Card: TBD
Created: 2026-11-03
Updated: 2026-11-03

## Goal

When the autopilot closes an escalated run nobody fixed within 72 hours, its carousel stops waiting for a human at
the same time, so the dashboard never shows a carousel waiting for review whose autopilot run is already closed.

## Problem

Found in a read-only prod triage on 2026-11-03. `RunRecovery._close_one`
(`modules/autopilot/application/run_recovery.py`) moves an `escalated` run older than 72 hours to `rejected` /
`escalation_expired` and never touches its carousel. Run `ff4f0952` was closed at 2026-11-02 18:38Z while its
carousel `295c1069` stayed `content / awaiting_human` for about 6 more hours, until the stuck-workflow auto-reject
(`WorkflowTimeoutRepository`) flipped it to rejected at 00:33Z. The carousel's `updated_at` was later than the run's,
so the reaper's 72-hour window ended later. Cosmetic, low risk, but the run and the carousel should agree.

## Scope

- When `_close_one` rejects an abandoned escalation, it also settles that carousel to the terminal rejected state
  the stuck-workflow auto-reject uses (`phase_status=rejected`, `status=failed`, `error_message`), emitting the same
  `project.phase_changed` event with the same payload keys.
- The reject transition is the existing `WorkflowTimeoutRepository` one, made public (`reject` + `RejectCause`) and
  reused; no second copy and no raw UPDATE.
- A dedicated autopilot port (`CarouselSettler` in `modules/autopilot/domain/recovery.py`), implemented in autopilot
  infrastructure on top of a new editorial public operation (`settle_abandoned_carousel`).
- Idempotent: a carousel that is not waiting for a human (rejected, approved for publish, public, published,
  archived, any other phase status) or whose lock version moved since the escalation is left alone; a second sweep
  does nothing.
- If the settle fails the run still closes and the failure is logged; the stuck-workflow auto-reject remains the
  backstop.

## Non-Goals

- `_expire_state` (`awaiting_owner` → `expired`, `owner_review_expired`). The same kind of gap exists: an expired
  owner review leaves its carousel at `final_review / awaiting_human` until the stuck auto-reject. It is **not** the
  same small change, so it is out of scope here:
  - the carousel is a finished draft the owner can still approve and publish from the website; rejecting it on the
    Telegram review timeout is a product decision, not a consistency fix;
  - an `awaiting_owner` run has no `escalated_version`; the "unchanged since" check would need the notice revision
    instead, a different rule.
  A follow-up needs the owner's call on whether an expired Telegram review should reject the carousel at all.
- `awaiting_thesis` expiry: no carousel exists yet.
- Changing the stuck-workflow auto-reject itself (eligibility, timeout, payload) or the carousel raw-update allowlist.

## Acceptance Criteria

- [x] AC1: closing an abandoned escalation whose carousel waits for a human (`awaiting_human`, not archived, not
  published, not approved for publish, not public) at the lock version the run escalated at moves the carousel to
  `phase_status=rejected`, `status=failed`, with the escalation reason as `error_message`.
- [x] AC2: that settle emits one `project.phase_changed` event with the stuck auto-reject's payload keys
  (`previous_phase`, `previous_phase_status`, `phase_status`, `reason`, `timeout_hours`) and a distinct `source`
  (`autopilot_escalation_expired`).
- [x] AC3: the transition is the stuck-workflow auto-reject's own (`WorkflowTimeoutRepository.reject`); no raw UPDATE
  on carousel tables, `check_carousel_raw_updates.py` allowlist unchanged.
- [x] AC4: a carousel not waiting for a human, or whose lock version moved since the escalation, is left unchanged and
  no event is emitted; a run with no carousel or no `escalated_version` settles nothing; a second sweep does nothing.
- [x] AC5: the run closes first; a lost close (CAS refused) settles nothing; a settle error is logged
  (`autopilot_escalation_settle_failed`) and the run stays rejected (the settle runs in a savepoint).
- [x] AC6: autopilot reaches the carousel only through a port and the editorial public facade (import-linter
  contracts unchanged and green).

## Gherkin Scenarios

`backend/tests/features/escalation_close_settles_carousel_ae0601.feature`

```gherkin
Feature: An abandoned escalation that closes also settles its carousel (AE-0601)

  Scenario: Closing an abandoned escalation rejects its waiting carousel
  Scenario: A carousel that is no longer waiting for a human is left alone
  Scenario: A carousel changed since the escalation is left alone
  Scenario: A run without a carousel or an escalation version settles nothing
  Scenario: A second sweep does nothing
  Scenario: A failed carousel settle still closes the run
  Scenario: A run whose close loses the race settles nothing
```

## Delta

### ADDED

- `CarouselSettle` command and `CarouselSettler` port (`modules/autopilot/domain/recovery.py`).
- `settle_abandoned_carousel` + `AbandonedCarouselSettle` (`modules/editorial/infrastructure/abandoned_carousel.py`,
  exported on `modules/editorial/public.py`).
- `EditorialCarouselSettler` adapter and `carousel_settler` factory (`modules/autopilot/infrastructure/carousel_settler.py`).
- `RejectCause` and the public `WorkflowTimeoutRepository.reject`.
- Constants for the escalation reject reason/source and the settle log events.

### MODIFIED

- `RunRecovery._close_one`: close the run first, then settle the carousel.
- `RecoveryDependencies` / `RunnerDependencies`: optional `carousels` port; the worker wiring sets it.
- `WorkflowTimeoutRepository.auto_reject_stuck` calls the shared `reject` with the stuck cause (same behaviour).

### REMOVED

- The private `WorkflowTimeoutRepository._reject` (replaced by the public `reject`).

## Affected Areas

- Backend: autopilot recovery, editorial facade, stuck-workflow auto-reject repository.
- Frontend: none.
- Database: no migration.
- API: none.
- Tests: unit (run recovery with fakes, settle eligibility, reject reuse), Postgres integration.
- Docs: none.
- Prompts/LLM: none.
- Observability: `autopilot_escalation_carousel_settled`, `autopilot_escalation_settle_failed` log events.
- Deployment: none.

## Dependencies

- Blocks: none
- Blocked by: none
- Related: AE-0210 (stuck-workflow auto-reject)

## Implementation Plan

1. Feature file, ticket, failing unit + Postgres tests.
2. Make the stuck auto-reject transition public with a cause; reuse it in an editorial settle operation guarded by
   `SELECT ... FOR UPDATE`, the eligibility check and a savepoint.
3. Autopilot port + adapter + wiring; `_close_one` settles after the run close.
4. Gates via `gate-capture.sh backend`.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-11-03 10:00

Ticket created from the read-only prod triage. Feature file and failing tests first.

### 2026-11-03 11:30

Commit 1: ticket, feature, failing unit + Postgres tests (collection fails on the missing settle port and
constants). Commit 2: the fix. Unit (9) and Postgres integration (10) tests green. Full backend gate run via
`gate-capture.sh backend`.

## Files Touched

- `backend/src/rag_backend/modules/autopilot/application/run_recovery.py` — close first, then `_settle_carousel`.
- `backend/src/rag_backend/modules/autopilot/domain/recovery.py` — `CarouselSettle`, `CarouselSettler`.
- `backend/src/rag_backend/modules/autopilot/infrastructure/carousel_settler.py` — adapter + factory (new).
- `backend/src/rag_backend/modules/autopilot/application/runner_deps.py`, `runner.py`, `bootstrap.py` — wiring.
- `backend/src/rag_backend/modules/autopilot/recovery_constants.py` — settle log events.
- `backend/src/rag_backend/modules/editorial/infrastructure/abandoned_carousel.py` — settle operation (new).
- `backend/src/rag_backend/modules/editorial/public.py` — facade export.
- `backend/src/rag_backend/infrastructure/database/workflow_timeout_repository.py` — public `reject` + `RejectCause`.
- `backend/src/rag_backend/domain/constants/workflow_timeout.py` — escalation reject message and source.
- `backend/src/rag_backend/infrastructure/database/carousel_run_guard.py`,
  `backend/tests/unit/infrastructure/test_carousel_run_guard.py` — docstring reference to the renamed method.
- `backend/tests/features/escalation_close_settles_carousel_ae0601.feature` (new).
- `backend/tests/unit/modules/autopilot/test_escalation_close_settles_carousel_ae0601.py` (new).
- `backend/tests/integration/test_escalation_close_settles_carousel_pg_ae0601.py` (new).

## Test Evidence

- Unit: `tests/unit/modules/autopilot/test_escalation_close_settles_carousel_ae0601.py` 9 passed.
- Postgres: `tests/integration/test_escalation_close_settles_carousel_pg_ae0601.py` 10 passed.
- Full gate run (`gate-capture.sh backend`): pass 26, fail 0, skip 1 (mutation, CI only). See
  `.agent/reports/AE-0601.dev-summary.md`.

## QA Report

Pending.

## Decision Log

- Ordering: the run closes first, then the carousel is settled. The run's CAS transition is the claim: if another
  worker moved the run (woke it, closed it), the carousel is never touched. Settling first could reject a carousel
  whose run was just woken for the owner. If the settle fails, the carousel keeps waiting exactly as before this
  ticket and the stuck-workflow auto-reject still rejects it; the settle runs in a savepoint so its failure cannot
  roll back the run close.
- "Unchanged since" is the run's `escalated_version` against the row's `lock_version`, read under `FOR UPDATE`. A run
  without an `escalated_version` settles nothing (no proof the owner did not act).
- Port: a small dedicated `CarouselSettler` instead of a new `EditorialDriver` method, so the many `EditorialDriver`
  fakes stay unchanged and the port carries only this one operation. Optional on the dependency bundles like the
  other recovery-time ports; the worker wiring always sets it.
- The settle keeps the stuck path's transition as-is, so it does not bump `lock_version` (same as the auto-reject).

## Blockers

None.

## Final Summary

An abandoned escalation's close now settles its waiting carousel through the stuck auto-reject's own transition and
event. Awaiting QA.
