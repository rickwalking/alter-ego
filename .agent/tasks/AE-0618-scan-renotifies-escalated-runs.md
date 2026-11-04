# AE-0618 — The daily recovery scan re-sends the escalation notice with Retry once to stuck runs

Status: In Development
Tier: T2
Priority: Medium
Type: Feature
Area: Backend (autopilot notices, generation queue daily scan)
Owner: Pedro Marins
Agent Lane: developer → qa → release
Branch: feat/ae-0618-scan-renotifies-escalated-runs
Kanban Card: TBD
Created: 2026-11-04
Updated: 2026-11-04

## Goal

Pedro's decision (2026-11-04): the daily clean-up routine gives failed or escalated runs that are still unresolved
another chance to be retried, by re-sending the escalation notice that carries the owner's Retry button (AE-0606). A
run gets this at most once.

## Problem

Since AE-0606 (#351) the escalation notice carries the owner's carousel Retry. Notices are one-shot: the outbox event
is delivered once and deduped through the run's `notice_log`. Runs escalated or failed before that deploy got a notice
without the button and never get another, so they stay stuck unless the owner opens the website.

## Scope

- A new step in the daily recovery scan, after the two revive steps and before the purge.
- Eligibility: an autopilot run in `escalated` or `failed`, with a carousel, not closed by the owner or by a retry,
  without the re-notify marker and with no escalation event since Retry shipped; its carousel is not archived, not
  rejected, not approved, not published and not running.
- One new `content.autopilot.escalation_renotice` outbox event per eligible run, read by the existing notifier as
  KIND_ESCALATED, so the keyboard comes from the existing `status_keyboard()`.
- The marker `scan_renotified` in the run's `notice_log`, in the same transaction as the event.
- The count, and any item failure, in the summary Pedro already receives.

## Non-Goals

- A repeat cadence. At most once per run, ever.
- Any change to run state, carousels, lock versions or `updated_at`. No raw SQL update, no direct Telegram call.
- Any change to the notices of other kinds, to `OwnerNotificationService` or to the scan's other steps.
- The website (`frontend/`).

## Acceptance Criteria

- [x] An eligible escalated run gets exactly one event; the notifier sends it with the carousel Retry keyboard.
- [x] A second scan sends nothing for it, even when the first notice was not delivered yet.
- [x] Rejected, approved, published, archived and running carousels are skipped, as are runs already notified with
      Retry, and a failed run with a rejected carousel.
- [x] A failing item is logged and reported and does not stop the others; a failing listing does not stop the scan.
- [x] The summary carries the count.
- [x] Nothing changes run state, reason, `updated_at`, or the carousel.

## Gherkin Scenarios

See `backend/tests/features/scan_escalation_renotice_ae0618.feature`.

## Delta

### ADDED

- Event type `content.autopilot.escalation_renotice`, marker `scan_renotified`.
- `AutopilotRenoticeBridge` (autopilot) and the `EscalationRenotifier` port (generation queue).

### MODIFIED

- `notice_kind` maps the new event to KIND_ESCALATED; `NOTIFY_EVENT_TYPES` includes it.
- `DailyRecoveryScan`, `ScanReport`, `summary_text`, the scan's composition and its done log.

### REMOVED

- Nothing.

## Affected Areas

- Backend: `modules/autopilot`, `modules/generation_queue`, `worker/recovery.py`
- Frontend: none
- Database: no migration; one outbox row and one ledger entry per run
- API: none
- Tests: new unit and integration tests, plus `.feature`
- Docs: this ticket
- Prompts/LLM: none
- Observability: the scan's done log carries the count; a new item-failed log
- Deployment: the first 04:00 São Paulo scan after the deploy sends the notices

## Dependencies

- Blocks: none
- Blocked by: none
- Related: AE-0606, AE-0524, AE-0553

## Implementation Plan

1. `.feature`, then tests that fail.
2. Autopilot: event type, marker, eligibility, staging.
3. Generation queue: port, carousel filter, scan step, summary, composition.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-11-04

Ticket created. `.feature` and failing tests first, then the code. Implementation and cheap gates done.

## Files Touched

- Autopilot: `domain/escalation_renotice.py`, `infrastructure/escalation_renotice.py`,
  `infrastructure/renotice_record.py`, `renotice_bridge.py`, `renotice_constants.py`; `notify_constants.py` and
  `domain/messages.py` (event type and its kind).
- Generation queue: `application/recovery_scan.py`, `domain/recovery.py`, `bootstrap.py`,
  `infrastructure/escalation_renotifier.py`, `renotify_constants.py`.
- Worker: `worker/recovery.py` (the count in the done log).
- Tests: the new feature, unit and integration files; `DailyScanDependencies` gained a required field, so four
  existing test files pass it; `tests/integration/queue_flow_db_support.py` adds the notifier's cursor table.

`notifications.py`, `status_keyboard.py`, `queue_bridge.py`, `dispatcher.py`, `infrastructure/repository.py`,
`generation_queue/constants.py` and `frontend/` are unchanged.

## Test Evidence

- Failing first: the three new test files failed at collection on the commit that holds only the tests.
- 81 passed on Postgres across the three new files; 1,393 passed across `tests/unit/modules/autopilot`,
  `tests/unit/modules/generation_queue` and the daily-scan integration files.
- Line and branch coverage: 100% on the new files and `recovery_scan.py` (targeted run, 99 passed).
- PR #360 CI at `8ade4019`: all checks passed, mutation included.
- PR #360 CI at `7011e232`: all checks passed, `backend-gate` on its second attempt. The first failed on
  `test_cancelled_event_writes_leave_the_workflow_intact` (`assert events == []`), a timing test this change does not
  touch; `Test & Coverage` passed at the same head and the one rerun passed (run 41872220335).
- Without Postgres the concurrent-scans test is skipped through `requires_postgres`: it needs real row locks.
- Cheap gates green (see the dev summary). Full gate: lead's heavy slot.

## QA Report

Pending.

## Decision Log

1. **"Already had a Retry notice" test.** A run is skipped when the outbox holds a `content.autopilot.state_changed`
   event for it with `state=escalated` created at or after `CAROUSEL_RETRY_SHIPPED_AT` (2026-11-04T09:21:21Z, the end
   of the deploy of #351, `f81c4cc9`). The event counts whether or not it was delivered yet: a run escalated minutes
   before the scan must not get two notices. An event in the merge-to-deploy gap counts as before Retry, so that run
   gets the notice, which is the safe side.
2. **Marker written at emit, not at delivery.** The marker goes into `statuses` in the transaction that writes the
   outbox row, under a row lock, the way `daily_recovery` already does. If it were written at delivery, a notice still
   waiting in the outbox the next day would be emitted again. The notifier then records the event id in `statuses` as
   for any status notice, so `scan_renotified` plus the event id is the sent proof. The cost: a notice dropped after
   three failed sends is not offered again. That is what "at most once" asks for.
3. **New event type instead of a second `state_changed`.** No state changed, and `state_changed` means a transition
   to anything reading the outbox or the audit log. A dedicated type also makes a failed run's notice KIND_ESCALATED,
   as asked; a `state_changed` with `state=failed` would be KIND_FAILED, which has no Retry.
4. **Parked runs keep their own keyboard.** A run with reason `queue_dead_letter:*` goes through the same
   `status_keyboard()`, so it gets "Tentar de novo" and "Descartar". The carousel Retry would be refused with
   `use_reprocess` on those runs. AE-0606 kept the button off them for the same reason.
5. **Carousel check on the generation queue side.** `autopilot-editorial-facade-only` forbids the autopilot from
   reading the carousel model, and `editorial/public.py` has no read of these columns and is in open work. The port
   adapter in `generation_queue/infrastructure`, which already reads that model, filters the candidates.
6. **A new narrow port, not `ParkedAutopilot`.** That port is implemented by `queue_bridge.py`, which is in parallel
   open work. New constants are in `generation_queue/renotify_constants.py`, because `constants.py` is too.
7. **"Still unresolved".** Closed reasons are `owner_queue_cancelled`, `owner_queue_discard`, `owner_queue_retry` and
   `queue_daily_recovery`. On the carousel, the rule mirrors the Retry's own `_finished` guard, plus `in_progress` and
   `archived_at`. A running carousel is skipped without a marker, so a later scan can still pick it up.
8. **Summary.** The line appears only when N > 0 or an item failed, so a quiet day's summary stays byte-identical.
9. **No repeat cadence** was built, and none is proposed.
10. **`notice_kind`.** Adding a branch would pass the return-count limit, so the three fixed event types moved into a
    lookup table. Behaviour for the existing types is unchanged.

## Blockers

The move to Dev Complete needs the `GATES_JSON` line of a full gate run in the dev summary (`move_ticket.py` refuses it
otherwise). That run is pending, so the status stays In Development; it was not forced.

## Final Summary

The daily scan now emits one `content.autopilot.escalation_renotice` event, with its ledger marker, for each stuck run
that never got the Retry, and reports the count. From the read-only check of 2026-11-04, the first scan after
the deploy should pick runs b5f5ff39, a8a3b196, 66873e0d and 92bdb9d9 and skip the two failed runs of 2026-10-18, whose
carousels were auto-rejected. This code has not been run against production data.
