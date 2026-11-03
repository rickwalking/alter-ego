# AE-0604 — A carousel reject bumps lock_version so a stale owner review is refused

Status: Dev Complete
Tier: T1
Priority: Medium
Type: Bug
Area: Backend, carousel workflow (stuck auto-reject, abandoned-escalation settle, review CAS)
Owner: Pedro
Agent Lane: developer → qa → release
Branch: fix/ae-0604-reject-bumps-lock-version
Kanban Card: TBD
Created: 2026-11-03
Updated: 2026-11-03

## Goal

Once a carousel is rejected by the system (stuck-workflow sweep or abandoned-escalation settle), an owner review
action sent with the version the owner read before the reject is refused with the existing version-conflict
response, instead of driving a rejected carousel.

## Problem (root cause, confirmed in code)

All paths below are under `backend/src/rag_backend/`.

- The one reject transition is `WorkflowTimeoutRepository.reject`
  (`infrastructure/database/workflow_timeout_repository.py:119`). It sets `phase_status=rejected`, `status=failed`
  and `error_message` (lines 133-135) and emits the phase-changed event. It never touches `lock_version`.
- Two callers run it:
  - the stuck-workflow sweep, `WorkflowTimeoutRepository.auto_reject_stuck`
    (`infrastructure/database/workflow_timeout_repository.py:88`, loop at :99-100), driven by the workflow worker
    tick (`application/workers/workflow_workers.py:191`);
  - the abandoned-escalation settle, `settle_abandoned_carousel`
    (`modules/editorial/infrastructure/abandoned_carousel.py:53`, reject at :71), driven by
    `RunRecovery._settle_carousel` (`modules/autopilot/application/run_recovery.py`) through the
    `EditorialCarouselSettler` adapter (`modules/autopilot/infrastructure/carousel_settler.py`).
- Every owner review CAS compares `lock_version` only:
  - `POST /carousels/{id}/workflow/resume` (`api/routes/carousels/editorial_workflow.py:275`) reads the row, checks
    `ensure_resume_not_in_progress` (`api/routes/carousels/editorial_workflow_routes_validate.py:135`, which only
    refuses `in_progress`), then calls `bump_resume_lock_version`
    (`api/routes/carousels/editorial_workflow_routes_validate.py:299`) →
    `CarouselProjectWriteOwner.bump_resume_lock_version`
    (`modules/editorial/infrastructure/carousel_project_write_owner.py:196`) →
    `OptimisticLockService.bump_carousel_version` (`application/services/optimistic_lock_service.py:93`), whose
    check (`:113-114`) and `UPDATE ... WHERE lock_version = current` (`:116-123`) look only at `lock_version`.
    A mismatch raises `ERR_VERSION_CONFLICT`, mapped to the typed 409 `version_conflict`
    (`editorial_workflow_routes_validate.py:316-320`).
  - The same CAS is reused by the autopilot driver and Telegram approve (`modules/autopilot/application/owner_approval.py:74`
    → editorial driver), manual recovery (`modules/generation_queue/infrastructure/manual_recovery_store.py:216`),
    owner autofix (`application/services/carousel/owner_autofix_lock.py:55`), the automation run
    (`modules/editorial/infrastructure/carousel_automation_run.py:88`), `carousel_lock_cas.py:23` and the
    presentation write owner (`modules/presentation/infrastructure/presentation_write_owner.py:175`).

The race: the owner reads the carousel at version N while it awaits review; the sweep or the settle rejects it and
leaves it at N; the owner's approve at `expected_version=N` passes the CAS (N == N), bumps to N+1 and queues a resume
that drives a rejected carousel.

## Scope

- `WorkflowTimeoutRepository.reject` bumps `lock_version` by one in the same unit of work as the phase-status flip
  (ORM attribute write on the row it already holds, flushed with the rest of the reject; no raw UPDATE, the
  `check_carousel_raw_updates.py` allowlist stays unchanged).
- Both callers get it for free; the caller still commits.
- A stale owner CAS at N then fails with the existing 409 `version_conflict` (no new mechanism, no new response).

## Non-Goals

- The sweep window, the stuck timeout and the 72-hour escalation expiry are unchanged.
- Refusing a resume on an already rejected carousel at the *current* version. The resume route has no
  `phase_status=rejected` guard today (only `in_progress` is refused), so an approve at the post-reject version is
  still accepted as before. Whether a rejected carousel may be resumed from the website is a product decision; see
  the Decision Log and the follow-up below.
- The sweep's `SELECT` is not `FOR UPDATE` (unchanged): an owner CAS that commits between the sweep's read and its
  flush is still overwritten by the reject, as before this ticket. Pre-existing, very narrow (the row must have been
  idle for the whole stuck window), left as a follow-up.

## Acceptance Criteria

- [x] AC1: after the stuck sweep rejects a carousel the owner read at version N, the owner's resume at
  `expected_version=N` is refused with 409 `version_conflict`, and the row stays rejected.
- [x] AC2: the same after the abandoned-escalation settle rejects it.
- [x] AC3: the reject leaves `lock_version` at N+1 (one bump per reject); a carousel the sweep or the settle leaves
  alone keeps its version.
- [x] AC4: a resume at the current version on a carousel that was not rejected is still accepted (202).
- [x] AC5: the settle guard (`lock_version == escalated_version` read under `FOR UPDATE`) still settles once and a
  second sweep does nothing; AE-0601 tests green (the one assertion that pinned the old, unbumped version updated).
- [x] AC6: no gate, allowlist, baseline or threshold loosened.
- [x] AC7: a Telegram approve, publish-now or schedule tap on a review sent before the carousel was rejected closes
  the run (`awaiting_owner -> rejected`, reason `carousel_rejected`) instead of moving it to `reworking`; nothing is
  approved or released.

## Gherkin Scenarios

`backend/tests/features/reject_bumps_lock_version_ae0604.feature`

```gherkin
Feature: A carousel reject bumps lock_version so a stale owner review is refused (AE-0604)

  Scenario: A stale owner approve after a stuck-sweep reject is refused
  Scenario: A stale owner approve after an escalation-close settle is refused
  Scenario: An approve at the post-reject version is handled as before
  Scenario: An owner action at the current version on a waiting carousel still works
  Scenario: The reject bumps the lock version once
  Scenario: A Telegram review tap after a reject closes the run
```

## Delta

### MODIFIED

- `WorkflowTimeoutRepository.reject`: also bumps `lock_version`.
- `tests/integration/test_escalation_close_settles_carousel_pg_ae0601.py`: the settled carousel is now at
  `_VERSION + 1` (that assertion pinned the bug).

### ADDED

- Feature file, Postgres route test, unit tests for the bump.

## Affected Areas

- Backend: stuck auto-reject repository (both reject callers).
- Frontend: none (a stale client already handles the typed 409 `version_conflict`).
- Database: no migration.
- API: no contract change; a stale resume after a system reject now returns the existing 409.
- Tests: unit + Postgres integration.
- Docs, prompts, observability, deployment: none.

## Dependencies

- Blocks: none
- Blocked by: none
- Related: AE-0601 (escalation-close settle), AE-0210 (stuck-workflow auto-reject)

## Implementation Plan

1. Ticket with the root cause, feature file, failing Postgres route test (stale approve after sweep / settle).
2. Bump `lock_version` in `reject`; update the AE-0601 assertion; unit tests for the bump.
3. Touched + related tests, single gates (lint, type, comments, format, lint-diff, gherkin-refs, docstrings).

## Other version readers checked

- AE-0601 settle guard (`abandoned_carousel.py:75-87`): compares `lock_version` to `escalated_version` under
  `FOR UPDATE` *before* calling `reject`, so the bump happens after the check. A second sweep stops at
  `phase_status != awaiting_human` before the version check. Unaffected.
- `RunRecovery._fixed_at_new_version` / `_back_at_final_review` (`run_recovery.py:347-359`): compare
  `escalated_version` to the current `lock_version`, but only after `_at_final_review` requires
  `phase_status == awaiting_human` at final review. A rejected carousel never passes that, and `_check_one`
  (`run_recovery.py:279`) closes the run on `rejected` first. The bump cannot make a rejected carousel look "fixed at
  a new version".
- `manual_recovery_classifier._version_refusal` (`modules/generation_queue/domain/manual_recovery_classifier.py:44-49`):
  a manual recovery sent with the pre-reject version is now refused `STALE_VERSION` (it would also fail the CAS in
  `manual_recovery_store.py:216`). Correct: the operator saw a different row.
- Autopilot CAS callers that read the snapshot and then CAS on its `lock_version` (`runner.py:287/313`,
  `gate_repair.py:131`, `rework_step.py`, `slide_autofix.py:232`, `owner_approval.py:74`): a snapshot read before the
  reject now fails its CAS instead of driving the rejected carousel. Intended.
- Telegram review revision guard (`modules/autopilot/application/review_revision_guard.py`): with the bump, an owner
  tap on a review sent at N, after the carousel was rejected at N+1, became outdated and moved the run to
  `reworking` (`review_outdated`), where the policy WAITs on a rejected carousel (`domain/policy.py:79`) and nothing
  closes it. Regression introduced by the bump; fixed here (AC7, see the Decision Log).
- `queue_board` / `snapshot` / notices carry `lock_version` for display or as a revision key only.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-11-03

Root cause confirmed in code (above). Ticket and feature file written; failing Postgres route test next.

Commit 1: ticket, feature, Postgres route test. On the unfixed code 3 of 4 fail: both stale approves return 202
and flip the rejected row to `in_progress` (the bug), and the post-reject version is still N.

Commit 2: `reject` bumps `lock_version`; the carousel model's `lock_version` is declared `Mapped[int]` so the ORM
write type-checks (same column, schema-drift PASS); the AE-0601 Postgres assertion that pinned the unbumped version
now expects `_VERSION + 1`; unit tests for the bump.

## Files Touched

- `backend/src/rag_backend/modules/autopilot/application/review_revision_guard.py` — close the run on a rejected
  carousel; the outdated branches moved to `_outdated` (return-count lint).
- `backend/src/rag_backend/modules/autopilot/application/owner_approval.py` — `carousel_rejected`.
- `backend/tests/unit/modules/autopilot/test_review_tap_after_reject_ae0604.py` (new).
- `backend/src/rag_backend/infrastructure/database/workflow_timeout_repository.py` — `reject` bumps `lock_version`.
- `backend/src/rag_backend/infrastructure/database/models/carousel.py` — `lock_version: Mapped[int]` (same column).
- `backend/tests/features/reject_bumps_lock_version_ae0604.feature` (new).
- `backend/tests/integration/test_reject_bumps_lock_version_pg_ae0604.py` (new).
- `backend/tests/unit/infrastructure/test_reject_bumps_lock_version_ae0604.py` (new).
- `backend/tests/integration/test_escalation_close_settles_carousel_pg_ae0601.py` — settled version is `_VERSION + 1`.

## Test Evidence

- New Postgres route test: 4 passed (3 failed before the fix).
- New unit tests: 3 passed.
- Telegram tap after reject (`test_review_tap_after_reject_ae0604.py`, 3 cases): failed first (run left in
  `reworking`), passes after the guard change. `tests/unit/modules/autopilot` + `test_autopilot_owner_actions.py`:
  1050 passed. Autopilot/review integration files plus the earlier related set: 522 passed.
- AE-0601 unit (9) and Postgres (10) tests: passed.
- 31 related test files (stuck auto-reject, run guard, workflow workers, archive, resume routes, manual recovery,
  run recovery, escalation settle) plus the new ones, in collection order: 250 passed.
- Single gates: format, lint, lint-diff, strict-diff, type, comments, docstrings, gherkin-refs, blanket-ignore,
  integrity, schema-drift, imports PASS (rerun after the guard change: format, lint, lint-diff, type, comments, docstrings,
  gherkin-refs, integrity, imports PASS); `check_carousel_raw_updates.py` OK. Full gate: lead's heavy slot.

## QA Report

Pending.

## Decision Log

- ORM bump instead of a raw CAS `UPDATE`: the row is already in the session (the sweep loaded it, the settle holds it
  under `FOR UPDATE`), and a raw `update(CarouselProjectModel)` would need a new entry in the carousel raw-update
  allowlist. The bump is flushed in the same `UPDATE` as `phase_status=rejected`.
- `lock_version` on `CarouselProjectModel` declared `Mapped[int] = mapped_column(...)` instead of a bare `Column`:
  mypy strict rejects an `int` assignment to `Column[int]`. Same type, default and nullability; schema-drift PASS.
- Telegram regression: closed in `RevisionGuard.check`, the place that moved the run to `reworking`. Once a tap is
  known to be outdated, the guard asks `FinalReviewApproval.carousel_rejected` (a gate read, `phase_status ==
  rejected`); if so the run moves `awaiting_owner -> rejected` with the existing `REASON_CAROUSEL_REJECTED` (the
  reason `RunRecovery._check_one` closes escalated runs with, which also sends the existing "closed" notice) and the
  tap is answered with the existing `TEXT_REJECTED`. No new constant. Chosen over a `reworking` policy close
  because it stops the run from entering `reworking` at all, touches only the revision-guarded taps (the path the
  bump changed), and leaves the runner's WAIT policy for every other state untouched. The close uses
  `TransitionCommand.moving` (terminal; no 72-hour anchor to keep). `awaiting_owner -> rejected` is already in
  `ALLOWED_TRANSITIONS`.
- No new rejected-state guard on the resume route: the brief asked to keep what the route does today for a rejected
  carousel, and today it accepts a resume at the current version.

## Blockers

None.

## Follow-ups (not done here)

- Resume route has no `phase_status=rejected` guard: an approve at the post-reject version is accepted (202) and
  flips the rejected row to `in_progress`. Needs Pedro's call on whether a system-rejected carousel may be resumed
  from the website.
- The stuck sweep reads its rows without `FOR UPDATE`; an owner CAS committing between that read and the reject
  flush is overwritten (pre-existing, very narrow).
- Pre-existing, not caused by the bump: a run that is already `reworking` or `generating` when its carousel is
  rejected (for example a "revise" tap, which is not revision-guarded, on a carousel that is rejected) still WAITs
  under the policy. A policy-level close would cover those too; it is a wider change to the runner.
- `tests/unit/infrastructure/test_carousel_run_guard.py::test_timeout_auto_reject_clears_leftover_run_columns`
  is order-dependent (pre-existing): `uv run pytest tests/unit/infrastructure/test_workflow_timeout_repository.py
  tests/unit/infrastructure/test_carousel_run_guard.py` fails it (the session-scoped SQLite engine keeps the earlier
  file's stale rows, so its 1-hour sweep rejects 3 instead of 1); collection order (run guard first) passes.

## Final Summary

A system reject (stuck sweep or escalation settle) now bumps `lock_version` in the same flush, so an owner review
sent with the pre-reject version gets the existing 409 `version_conflict`. Awaiting QA.
