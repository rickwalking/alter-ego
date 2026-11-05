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
- [x] Runs parked by the queue, runs with no carousel and owner-cancelled runs are skipped. A parked notice or a failed
      publish notice that offered Retry counts as a Retry notice, on any run and at any date.
- [x] A run or carousel that changes between the listing and the stage gets no notice: every check runs again under
      the row lock.
- [x] Rows shaped like the seven production rows select exactly the three runs Pedro approved, with each skipped row
      exercising its exclusion on a carousel that is otherwise open.
- [x] A notice the notifier gave up on is queued again by the next scan; a delivered, pending or in-doubt one is not.
- [x] No run gets two delivered notices through a crash after the send, an outbox replay, two scans or two workers.
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

Third round: `application/notifications.py` (the claim; `status_notice` moved out to keep it under the file limit),
`application/renotice_send.py`, `application/status_notice.py`, `bootstrap_telegram.py`, `domain/exceptions.py`,
`infrastructure/telegram_notifier.py`.

`status_keyboard.py`, `queue_bridge.py`, `dispatcher.py`, `infrastructure/repository.py`,
`generation_queue/constants.py` and `frontend/` are unchanged.

## Test Evidence

- Failing first: the three new test files failed at collection on the commit that holds only the tests.
- Second round, failing first at `2fffb1fb`: 14 of 19 tests in `test_scan_renotice_eligibility_ae0618.py` failed on
  their assertions (parked runs, parked earlier, a failed publish that offered Retry, the races, the in-flight write).
  The publish tests at that commit used a wrong `outcome` value, corrected with the fix, so the no-Retry publish test
  passed there for the wrong reason. Passing there already, so regression pins and not fail-first: the seven-row
  selection, the no-Retry publish notice, and the owner retry and owner cancel races. No-carousel and owner-cancelled
  runs were already excluded and tested.
- 81 passed on Postgres across the three new files; 1,393 passed across `tests/unit/modules/autopilot`,
  `tests/unit/modules/generation_queue` and the daily-scan integration files.
- Line and branch coverage: 100% on the new files and `recovery_scan.py` (targeted run, 99 passed).
- Second round: 1,425 passed across `tests/unit/modules/autopilot`, `tests/unit/modules/generation_queue` and the
  daily-scan integration files, on Postgres; 100% line and branch coverage on the files it changed.
- Third round, failing first at `2d01a845`: on assertions, the second chance, the once-per-scan repeat, two scans after
  a give-up, the crash after the send (the notice went out twice) and the ledger of a delivered notice. The unit tests
  of the claim and the transport classes need names that did not exist there. Passing there already, so regression
  pins: a notice still being retried, a run that moved on, a rate limited send, an outbox replay, and the seven-row
  selection. The unknown outcome and real claim tests were added with the fix.
- Third round, seven-row selection: removing `REASON_OWNER_CANCELLED` from `RESOLVED_REASONS` fails it at the selection
  assert, because the owner-cancelled row now has an open carousel. The constant was restored.
- Third round: 1,460 passed across `tests/unit/modules/autopilot`, `tests/unit/modules/generation_queue` and the
  daily-scan integration files, plus 34 in the six autopilot notifier integration files, on Postgres; 100% line and
  branch coverage on `notifications.py`, `renotice_send.py`, `status_notice.py` and both `escalation_renotice.py` files.
- PR #360 CI at `8ade4019`: all checks passed, mutation included.
- PR #360 CI at `7011e232`: all checks passed, `backend-gate` on its second attempt. The first failed on
  `test_cancelled_event_writes_leave_the_workflow_intact` (`assert events == []`), a timing test this change does not
  touch; `Test & Coverage` passed at the same head and the one rerun passed (run 41872220335).
- Without Postgres the concurrent-scans test is skipped through `requires_postgres`: it needs real row locks.
- Cheap gates green (see the dev summary). Full gate: lead's heavy slot.

## QA Report

Pending.

## Decision Log

1. **"Already had a Retry notice" test.** Pedro's rule is "never had a Retry-carrying notice", so a run is skipped when
   the outbox holds any event of it whose notice offered one, delivered or not, through `carried_retry()`:
   - a parked notice (`state_changed`, `escalated` or `failed`, reason `queue_dead_letter:*`), at any date;
   - a `publish_failed` notice that offered Retry, at any date;
   - any other escalation at or after `CAROUSEL_RETRY_SHIPPED_AT` (2026-11-04T09:21:21Z, the end of the deploy of #351,
     `f81c4cc9`). An escalation in the merge-to-deploy gap counts as before Retry, so that run gets the notice.
   A `failed` notice with any other reason offered no Retry and does not count: its run stays eligible.
2. **Marker written at emit, not at delivery; an undelivered notice gets another chance.** The marker
   (`scan_renotified:<event id>`) goes into `statuses` in the transaction that writes the outbox row, under the row
   lock, so a notice still waiting in the outbox the next day is not emitted again. This reverses the first version,
   where a notice dropped after three failed sends was never offered again: per Pedro's decision (2026-11-04), one
   notice per run, once ever, means one delivered, and a notice that was never delivered must get another chance. See
   decision 13.
3. **New event type instead of a second `state_changed`.** No state changed, and `state_changed` means a transition
   to anything reading the outbox or the audit log. A dedicated type also makes a failed run's notice KIND_ESCALATED,
   as asked; a `state_changed` with `state=failed` would be KIND_FAILED, which has no Retry.
4. **Parked runs are skipped.** Superseded by Pedro's decision (2026-11-04). This ticket first sent parked runs a
   notice with their own keyboard, but those runs already got "Tentar de novo" and "Descartar". `renotice_due` now
   refuses a `queue_dead_letter:*` reason, and decision 1 covers a run that was parked earlier and moved on.
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

11. **Pedro's decision (2026-11-04): the first scan after the deploy sends one notice, once ever, to 3 runs.**
    From the read-only production facts of that day, all in state escalated or failed unless noted:

    | Run | State and reason | Carousel | Result |
    |---|---|---|---|
    | b5f5ff39 | escalated `persona_score_below_threshold` | 6f36130e awaiting_human/pending | pick |
    | 66873e0d | escalated `content_quality` | 41c4f437 awaiting_human/pending | pick |
    | 92bdb9d9 | escalated `phase_failed` | 84a58b72 failed/pending | pick |
    | 1a5e5e86 | failed `owner_queue_cancelled` | none | skip: owner cancelled, no carousel |
    | 3ca56d78 | failed `engine_error` | rejected/failed | skip: carousel rejected |
    | 880d089f | failed `engine_error` | rejected/failed | skip: carousel rejected |
    | a8a3b196 | now `generating`, after an owner Retry | not checked | skip: no longer stuck |

    The selection stays rule-based, with no list of ids in the code. The test fixture reads the carousel pairs as
    `phase_status`/`status`.
12. **The stage repeats every check under the lock.** `stage()` locks the run, then re-checks state, reason, the marker,
    the past notices and the carousel. The autopilot may not read the carousel model, so the generation queue adapter
    passes `carousel_open`, which runs on the staging transaction. It takes a shared lock (`FOR SHARE`) on the carousel
    row until the commit: a write in flight is waited for and a later one waits for the marker, without blocking inserts
    that only reference the carousel.

13. **Another chance comes from the next daily scan.** The notifier has no mechanism that retries a dropped event type,
    and keeping one event open would stop its cursor, so a new event is the smallest change. `renotice_due` allows a new
    event only when every queued one is certainly undelivered: no event id in `statuses`, no claim, and no attempt left.
    A notice that keeps failing is queued once per scan. Each new event passes every check of decisions 1, 7 and 12.
14. **A claim before the send keeps it to one delivered.** The notifier records a send when its worker step commits, and
    that step goes on after the send, so a crash or a later failure in the step forgot a delivered notice and the next
    tick sent it again. Only for this event type, `SqlRenoticeClaims.take` commits `scan_renotice_sending:<event id>`
    under the row lock before the send. It is released only when the send certainly did not happen. A claim that stays
    closes that event and stops any new one. The early commit publishes only that step's own progress, since each
    worker step has its own commit. Other notices keep their behaviour.
15. **What counts as not sent.** A connect failure, a connect or pool timeout, a Telegram error answer, a rate limit and
    an unconfigured bot release the claim. A failure after the request left (read or write timeout, read error, protocol
    error) raises `TelegramDeliveryUnknownError`, a subclass, so every other caller behaves as before; it keeps the
    claim, as does any unexpected exception. When delivery is in doubt the notice is not repeated, so two limits remain:
    a worker that dies between the claim's commit and the send loses that notice, and a 5xx answer is read as not sent
    although a gateway error cannot prove it.

## Blockers

The move to Dev Complete needs the `GATES_JSON` line of a full gate run in the dev summary (`move_ticket.py` refuses it
otherwise). That run is pending, so the status stays In Development; it was not forced.

## Final Summary

The daily scan now emits one `content.autopilot.escalation_renotice` event, with its ledger marker, for each stuck run
that never got the Retry, and reports the count. From the read-only check of 2026-11-04, the first scan after
the deploy should pick runs b5f5ff39, 66873e0d and 92bdb9d9, the three Pedro approved (decision 11, with the skip
reasons of the other four). This code has not been run against production data.
