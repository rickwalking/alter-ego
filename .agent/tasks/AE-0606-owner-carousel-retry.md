# AE-0606 — Owner Retry for failed, blocked, escalated and rejected carousels (backend)

Status: Dev Complete
Tier: T2
Priority: High
Type: Feature
Area: Backend (generation queue, editorial resume, autopilot Telegram, carousel workflow routes)
Owner: Pedro Marins
Agent Lane: architect → developer → qa → release
Branch: feat/ae-0606-owner-carousel-retry
Kanban Card: TBD
Created: 2026-11-03
Updated: 2026-11-03

## Goal

The carousel owner can retry a carousel whose phase failed, whose gate is blocked, whose autopilot run escalated,
or that the system rejected, from the website (`POST /carousels/{id}/workflow/retry`) and from Telegram
("🔁 Tentar de novo" on an escalation notice). An owner approve on a rejected carousel is refused: Retry is the
only way back. This ticket is the backend half; the website button is PR2 (frontend).

## Problem

- A failed phase whose checkpoint is parked before its node (84a58b72, 74d35153) has no owner action: the
  website's failed card only restarts the whole workflow, and the queue's reprocess only handles stuck runs.
- A gate blocked by the engine (6f36130e, content, `content_approve_blocker` true) with its autopilot run
  escalated stays escalated: the run-recovery wake only wakes a run that is back at final review
  (`run_recovery.py` `_fixed_at_new_version` / `_back_at_final_review`).
- A carousel the system rejected (the stuck sweep or the abandoned-escalation settle) keeps `current_phase`, sets
  `phase_status=rejected` and `status=failed`; the website approve at the current lock version still drove it, and
  nothing re-ran its phase.

## Scope

- One shared backend action in `modules/generation_queue` (facade `retry_public.py`):
  - pure decision `domain/owner_retry.py` (`decide_retry`): `redrive` (checkpoint parked before a node), `revise`
    (blocked gate, failed phase with its gate open, rejected at a gate), `reopen` (rejected at the final review);
  - application service `application/owner_retry.py`, feedback line `application/owner_retry_feedback.py`;
  - infrastructure: facts under the row lock (`owner_retry_facts.py`), the savepoint write (`owner_retry_store.py`),
    the audit (`owner_retry_audit.py`).
- One transaction: `SELECT … FOR UPDATE` on the carousel row (`CarouselProjectWriteOwner.lock_for_retry`), facts,
  decision, then in a savepoint: the editorial `claim_automation_phase` (in-progress guard, revision cap, lock CAS,
  `in_progress` flip), status restore of a rejected carousel, the queued resume stage (dedupe key project plus the
  new lock version), the escalated run's CAS `escalated → generating` (`owner_carousel_retry`); then the audit
  `carousel.retry.requested`; then the commit (website) or the webhook's commit (Telegram).
- `claim_automation_phase` is the pre-run half of `run_automation_phase`, extracted without a commit;
  `run_automation_phase` keeps calling it unchanged.
- Website route `api/routes/carousel_retry.py`: `POST` (202 `{accepted, retry_kind, current_phase, phase_status,
  lock_version, autopilot_run_id}`) and `GET` capability `{can_retry, retry_kind, refusal_code, lock_version}`.
- Telegram: `ap:cr:<run uuid>` button on escalation notices that are not queue dead letters, mixin
  `application/carousel_retry_actions.py`, port `CarouselRetrier` (`domain/carousel_retry.py`), adapter
  `infrastructure/carousel_retrier.py` bound in `bootstrap_webhook.py`. `owner_actions.py` helpers moved to
  `owner_action_helpers.py` to stay under 400 lines.
- Approve on a rejected carousel is refused on every path:
  - website resume route: 409 typed `carousel_rejected` (`CONFLICT_CODE_CAROUSEL_REJECTED`), no state change;
  - Telegram approve / publish-now / schedule tap: the revision guard checks the rejected carousel first, closes the
    run `awaiting_owner → rejected` (`carousel_rejected`, as AE-0604 does for an outdated tap) and says so;
  - the run-owned editorial path (`claim_automation_phase`): `ValueError("carousel_rejected")`, mapped to
    `ResumeStatus.CAROUSEL_REJECTED` and its own owner text.

## Non-Goals

- The website button, the "Start over" placement and i18n (PR2, frontend).
- A `rejected → generating` autopilot transition (Pedro's decision, 2026-11-03: a closed run is not revived).
- Any change to the manual Revise rule (feedback stays required) or to the reprocess action.

## Acceptance Criteria

- [x] A parked failed phase is re-driven at the bumped lock version; the row is `in_progress`; one audit.
- [x] A blocked or failed open gate is revised with a fixed, system-written feedback line naming the reason; the
      same line is stored in the audit; the revise counts against the revision cap of 5.
- [x] An escalated (not dead-letter) autopilot run moves `escalated → generating` with `owner_carousel_retry` in
      the same transaction; Telegram edits the message to "🔁 Refazendo a fase {phase}…".
- [x] A rejected carousel is retryable: a gate re-runs its phase and the status goes back to `pending`; a final
      review is reopened (`awaiting_human`, status `completed`), nothing staged. A missing checkpoint refuses
      `no_checkpoint`.
- [x] Refusals change nothing and are typed: `not_found` 404, `not_owner` / `not_assigned_reviewer` 403, and 409
      `not_retryable`, `resume_already_in_progress`, `mutation_in_progress`, `use_reprocess`, `autopilot_active`,
      `no_checkpoint`, `version_conflict`, `revision_cap_exceeded`, `concurrent_update`.
- [x] A lost CAS (lock version or autopilot run) rolls back the stage, the status change and the audit.
- [x] An owner approve on a rejected carousel is refused on the website (409 `carousel_rejected`), on Telegram and
      on the run-owned path.

## Gherkin Scenarios

`backend/tests/features/carousel_owner_retry_ae0606.feature` (21 scenarios: happy, edge, failure, approve on a
rejected carousel). The AE-0604 scenario "An approve at the post-reject version is handled as before" is
superseded by Pedro's decision (2026-11-03) and now reads "… is refused as carousel_rejected".

## Delta

### ADDED

- `modules/generation_queue/{retry_public.py, domain/owner_retry.py, domain/owner_retry_ports.py,
  application/owner_retry.py, application/owner_retry_feedback.py, infrastructure/owner_retry_facts.py,
  infrastructure/owner_retry_store.py, infrastructure/owner_retry_audit.py}`
- `agents/prompts/owner_retry/v1/{retry_feedback.yaml, README.md}` (new prompt domain, no existing version edited)
- `api/routes/carousel_retry.py`, `api/schemas/carousel_retry.py`
- `modules/autopilot/{carousel_retry_constants.py, domain/carousel_retry.py,
  application/carousel_retry_actions.py, application/owner_action_helpers.py, infrastructure/carousel_retrier.py}`
- Tests: decision table, service, feedback line, store (SQLite + Postgres), route (Postgres), Telegram tap.

### MODIFIED

- `modules/editorial/infrastructure/carousel_automation_run.py`: `claim_automation_phase` extracted; approve on a
  rejected carousel raises `carousel_rejected`.
- `modules/editorial/infrastructure/carousel_project_write_owner.py`: `lock_for_retry`, `restore_active_status`.
- `api/routes/carousels/editorial_workflow_routes_validate.py`: approve at the current version on a rejected
  carousel is a 409 `carousel_rejected` (a stale one is still the CAS's `version_conflict`).
- `domain/constants/carousel_conflicts.py`, `domain/constants/carousel_workflow.py`: the new code.
- `modules/autopilot/application/review_revision_guard.py`: rejected check before the revision check.
- `modules/autopilot/domain/{gate.py, status_keyboard.py}`, `application/{owner_actions.py, schedule_steps.py}`,
  `infrastructure/editorial_driver.py`, `bootstrap_webhook.py`, `webhook_constants.py`.
- `docs/architecture/openapi.json`, `backend/tests/snapshots/openapi_routes.json` (new route).
- AE-0604 test and feature: the post-reject approve now expects 409 `carousel_rejected`; the escalated-notice
  keyboard assertion in `test_queue_position_ae0523.py` now expects the carousel Retry button.

### REMOVED

- None.

## Affected Areas

- Backend: generation queue, editorial, autopilot webhook, carousel workflow routes.
- Frontend: none in this PR (PR2).
- Database: none (no migration; ORM writes and a `FOR UPDATE` select only).
- API: new `GET/POST /api/carousels/{id}/workflow/retry`; resume route gains the 409 `carousel_rejected`.
- Tests: see Delta.
- Docs: OpenAPI artifact.
- Prompts/LLM: new `owner_retry/v1/retry_feedback.yaml`.
- Observability: `carousel_retry_accepted` / `carousel_retry_refused` logs; `carousel.retry.requested` audit.
- Deployment: none.

## Dependencies

- Blocks: AE-0606 PR2 (frontend Retry button).
- Blocked by: AE-0604 (merged: the reject bumps lock_version, which makes the auto-reject race safe).
- Related: AE-0552 (manual reprocess), AE-0601, AE-0604.

## Implementation Plan

1. Feature file, then the decision table and its tests.
2. Service, store, facts, audit; store tests on SQLite and Postgres.
3. Route and Telegram button; route tests on Postgres; Telegram tap tests.
4. Approve-on-rejected refusals on the three paths.

## QA Checklist

- [ ] Security reviewed (owner-only twice on Telegram; route owner check after the access check)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-11-03

Ticket created from the AE-0606 design plan and Pedro's decisions of 2026-11-03. Implemented the backend half with
the Telegram button and the approve-on-rejected refusals. Touched tests and the light backend gates run locally;
full gate: lead's heavy slot.

## Files Touched

See Delta.

## Test Evidence

Touched tests (Postgres `DATABASE_URL` and SQLite): 700 passed across the 71 test files that touch the changed
modules, including the new decision, service, store, route and Telegram tests. Light gates run individually; see
`.agent/reports/AE-0606.dev-summary.md`. Mutation runs in CI only (AE-0448). Full gate: lead's heavy slot.

## QA Report

Pending.

## Decision Log

- Pedro's decision (2026-11-03): a Retry counts as one revise against the cap of 5 (the editorial revision-cap
  check runs before the lock CAS; no bypass).
- Pedro's decision (2026-11-03): when the autopilot run is already closed (rejected after 72 h), Retry re-runs the
  carousel only. No `rejected → generating` run transition was added.
- Pedro's decision (2026-11-03): case B sends a fixed, system-written feedback line from a versioned prompt
  template (`owner_retry/v1/retry_feedback.yaml`, the repo's rule for text fed to the LLM) that names the
  escalation reason, else the engine's approve blocker, else `phase_failed` / `carousel_rejected`, with the
  persona score and the threshold when the score is below the floor. No empty-feedback path is opened; the manual
  Revise rule is unchanged. The line is stored in the `carousel.retry.requested` audit and the revise is tagged
  `feedback_source=autopilot` (the existing system source), so it is applied once and never re-fed as a human
  correction.
- Pedro's decision (2026-11-03): a rejected carousel is retryable; approved and published stay `not_retryable`.
  A missing checkpoint refuses `no_checkpoint` (no silent full restart).
- Pedro's decision (2026-11-03): an owner approve on a rejected carousel is refused; Retry is the only way back.
  On the website the refusal is 409 `carousel_rejected` at the current lock version; a stale approve is still the
  CAS's `version_conflict`, so AE-0604's stale-approve tests are unchanged and only its "handled as before"
  scenario (which Pedro's decision overrides) was updated.
- A carousel rejected at the final review is reopened (`awaiting_human`, status `completed`), not revised: the
  phase there is the owner's review, the content was already produced, and a revise would re-generate it. Retry
  at a rejected gate brings the status back to `pending` (the status of a carousel before export); the error
  message is kept as the last failure cause.
- `use_reprocess` is decided from the queue fences (a held dead-letter generation run, or an escalation whose reason
  is `queue_dead_letter:*`) rather than by running the manual-recovery classifier: every other stuck kind the
  classifier finds is an active run or an `in_progress` row, which Retry already refuses as
  `resume_already_in_progress`.
- The Telegram tap on a rejected carousel closes the run `awaiting_owner → rejected` with `carousel_rejected`, as
  AE-0604 does for an outdated tap: nothing else would ever close it. The carousel itself is not changed.
- The escalated run moved back to `generating` is driven by the dispatcher's safety net (an active autopilot state
  with no active generation run gets one staged), as the plan describes; Retry does not stage the drive itself.
- The `CarouselRetrier` port lives in `domain/carousel_retry.py` with the button and the parser, not in
  `owner_ports.py`, to keep the Telegram Retry pieces together.

- Review round 1 (2026-11-03):
  - The `in_progress` flip is the last write of the Retry's savepoint (after the stage and the run CAS), through
    `QuietRunStart.stage` (no event); the phase change and `run.started` are published by `QuietRunStart.announce`
    only after the commit: by the service on the website, by `OwnerActionService.deliver` after the webhook commit
    on Telegram (dropped on `discard`). `claim_automation_phase` gained `mark_in_progress=False` for this; the
    autopilot path is unchanged. `EditorialWorkflowService.mark_resume_in_progress` builds its state through the
    shared `resume_in_progress.in_progress_state` helper (same values).
  - `use_reprocess` only when the carousel's latest generation run is a dead letter and its autopilot run is still
    parked by the queue (reason `queue_dead_letter:*`) or absent: the reprocess classifier's rule. A discarded dead
    letter no longer blocks Retry.
  - The stuck sweep re-reads each row `FOR UPDATE SKIP LOCKED` with the same eligibility filter before it rejects,
    and returns the count it actually rejected. A select, not an UPDATE: the raw-update gate and its allowlist are
    unchanged. The reject stays in `WorkflowTimeoutRepository` (an infrastructure module that importing the editorial
    write owner from would make an import cycle through `abandoned_carousel`).
  - Lock order: the Retry locks the autopilot run row before the carousel row, the order of the 72-hour escalation
    close. Deadlock, serialization failure and lock timeout (`40P01`, `40001`, `55P03`) are caught in savepoints and
    refused as `concurrent_update`; any other database error still raises.
  - The capability (`GET`) and the Retry both refuse a revise at the revision cap (`revision_cap_exceeded`) from
    the checkpoint's counters, through the editorial cap-phase rule; the editorial cap check stays as the backstop.
- Review round 2 (2026-11-04): the post-commit announce is best effort (`carousel_retry_announce_failed` with
  the error class only) and the Telegram replies are delivered before it; tests prove a failed audit or commit
  announces nothing and propagates. The cap check is one shared helper (`revision_cap_reached`, used by
  `validate_revision_cap` and the Retry facts). The Telegram rejected check now reads the gate for approved
  carousels too (one read). `owner_actions.py` stays under 400 lines by moving `choice_deps` to
  `owner_action_helpers.py`.

- PR2, frontend (2026-11-04):
  - The website button is on the phase card: inside the failed card next to "Start over", above the phase content
    on a blocked or rejected carousel (Pedro's decision, 2026-11-03).
  - A `reopen` runs nothing, so no `run.finished` arrives: every 202 re-reads the workflow state, and the
    finished toasts follow only a retry accepted as `in_progress`.
  - `finishedOk` / `finishedFailed` come from the workflow state the page already follows (SSE): `awaiting_human`
    is ok; `failed` and `rejected` are failed. Tracking lives in the page, so a reload drops it.
  - The capability is keyed by phase, status and lock version, so a state change re-reads it. It is polled at the
    board interval while the refusal is temporary (`resume_already_in_progress`, `mutation_in_progress`,
    `autopilot_active`): an escalation changes neither the phase nor the lock version. It is not polled while the
    phase is `in_progress`, because the run's end changes the key.
  - The finished toasts are keyed on the version the accepted Retry moved past, not on a status edge. SSE can show
    `in_progress` before the 202 returns, and an edge watch then lost the toast and fired it for a later run. A
    state past that version that is not `in_progress` ends the watch, so no later run can show the toast.
  - A refusal is shown in a toast and next to the button, and clears when the workflow state changes.
  - A failed capability read hides the button without an error: Retry is an optional action on the card.
  - The publish page's failed notice keeps its label: its button only links back to the workspace, so
    "Start over" would be wrong there. `WorkflowFailedCard` takes `restartLabel`, passed by the workspace only.
  - `url-inventory.snapshot.json` regenerated for the new proxy route; it records routes and allows nothing.

## Blockers

None.

## Final Summary

Pending.
