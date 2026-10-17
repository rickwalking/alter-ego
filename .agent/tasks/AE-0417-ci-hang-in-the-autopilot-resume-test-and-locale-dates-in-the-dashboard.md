# AE-0417 — CI hang in the autopilot resume test + locale dates in the dashboard

Status: In Development
Tier: T2
Priority: P1
Type: Bug
Area: Cross-cutting
Owner: Claude (owner-requested fix, PR #132 follow-up + QA 2026-10-16 B24)
Agent Lane: developer → qa → release
Branch: fix/ae-0417-ci-hang-and-dates
Kanban Card: TBD
Created: 2026-10-17
Updated: 2026-10-17

## Goal

`backend/tests/integration/test_autopilot_resume_runs_phase.py` never hangs CI again, and a
hung test can no longer hold a runner for hours. Every date the dashboard shows follows the
active locale (pt "17/10/2026", en "Oct 17, 2026").

## Problem

1. **CI hang.** One `backend / Test & Coverage` run on PR #132 hung ~3 h; plain main hung
   2/30 locally. Every test PASSED, then pytest-asyncio's loop teardown sat in
   `asyncio.runners._cancel_all_tasks`. Reproduced on the Pi (2 hangs in 4 runs of the
   file). py-spy: main thread in `_cancel_all_tasks`, an aiosqlite connection thread idle.
   **Root cause:** `_execute_owned_run` (`editorial_workflow_resume_runner.py`) stopped the
   interval heartbeat with a bare `heartbeat.cancel()` and returned. `cancel()` only
   *requests* the stop: a heartbeat caught inside `write_run_heartbeat` outlived the run,
   wrote after the run's connections were gone (log: `carousel_run_heartbeat_failed … no
   active connection`), and at loop shutdown the leftover task's cancellation waited on a
   DB future that never resolved. No workflow had a `timeout-minutes`, so GitHub's 6 h
   default applied.
2. **English dates in the PT dashboard.** `formatBlogPostDate` and `formatDate` hardcoded
   `"en-US"` ("Oct 17, 2026" on Posts do Blog cards); the notification center, chat list,
   admin user table and calendar used the browser default or English date-fns tokens.

## Scope

1. Heartbeat helpers move to `editorial_workflow_run_heartbeat.py`; `stop_heartbeat`
   cancels **and waits** (`asyncio.wait`, so the heartbeat's own CancelledError is not
   re-raised while a cancel of the calling run still propagates). The run wrapper awaits it
   on every exit path.
2. `timeout-minutes`: backend Test & Coverage 30 (green runs 9-14 min), ci-gate
   backend-gate 90 (tests + mutation, 40-55 min), deploy `test` 40 (~15 min).
3. `faulthandler_timeout = 600` in `backend/pytest.ini` (pytest built-in) so a hang dumps
   every thread's stack.
4. `src/lib/locale-format.ts`: one locale helper (date, date+time, clock, relative, number)
   using the AE-0412 formats; `formatPublicDate` delegates to it.
5. Dashboard surfaces use `useLocale()`: blog list cards (date + views), notification
   center, chat list/messages, calendar (month title, weekday headers, event day label),
   knowledge document card, admin user table.

## Non-Goals

- No per-test timeout plugin: the repo does not use pytest-timeout; adding the dependency
  was out of scope by the brief.
- Non-date English strings in the calendar (legend, view modes, status labels) and the chat
  ("New conversation") — follow-up, not dates.
- Editor version history and the create-flow run banner: the history sidebar shows no dates;
  the banner's start clock is `HH:MM` (locale-neutral). No change.

## Acceptance Criteria

- [x] The run wrapper leaves no pending heartbeat task when it returns (unit test, seeded
      violation: a bare `cancel()` fails 3 of the 6 new tests).
- [x] A cancel of the calling run still propagates through `stop_heartbeat`.
- [x] The integration file runs 10/10 on the Pi without a hang (was 2 hangs in 4).
- [x] Backend test jobs have `timeout-minutes`; pytest dumps stacks after 600 s.
- [x] Posts do Blog cards show "17/10/2026" in pt and "Oct 17, 2026" in en.
- [x] Notifications, chat, calendar, knowledge and admin dates follow the active locale.
- [x] Public dates unchanged (`formatPublicDate` tests still pass).

## Gherkin Scenarios

Item 2: `frontend/tests/features/dashboard-locale-dates-ae0417.feature`.

Item 1 is CI/tooling + a cleanup fix with no user-visible behaviour change; see the
Decision Log for the "unit tests suffice" classification.

## Delta

### ADDED

- `backend/src/rag_backend/application/services/carousel/editorial_workflow_run_heartbeat.py`
- `backend/tests/unit/application/test_editorial_workflow_run_heartbeat.py`
- `frontend/src/lib/locale-format.ts` (+ test)
- `frontend/tests/features/dashboard-locale-dates-ae0417.feature`
- Tests: blog grid locale, notification center, chat adapter, calendar labels.

### MODIFIED

- `editorial_workflow_resume_runner.py`: start/stop the heartbeat through the new module.
- Integration tests `test_autopilot_resume_runs_phase.py`, `test_run_heartbeat_lock_pg.py`:
  the heartbeat-interval monkeypatch targets the module that now owns the loop.
- `.github/workflows/backend-quality-gates.yml`, `ci-gate.yml`, `deploy.yml`: timeouts.
- `backend/pytest.ini`: `faulthandler_timeout`.
- Frontend: `blog-posts/helpers.ts`, `blog-posts-grid.tsx`, `lib/utils.ts` (`formatDate`
  takes a locale, en default), `public-blog-text.ts`, `notification-center.tsx`,
  `chat-adapter.ts` (+ both chat views), calendar constants/helpers/grid/month hook,
  `document-card.tsx`, `user-table.tsx`.

### REMOVED

- `CALENDAR_WEEKDAY_HEADERS` (English constant; headers now come from Intl).

## Affected Areas

- Backend: carousel resume runner (heartbeat lifecycle).
- Frontend: dashboard date formatting.
- Database: none.
- API: none.
- Tests: new unit tests; two integration monkeypatch targets moved.
- Docs: this ticket.
- Prompts/LLM: none.
- Observability: none.
- Deployment: `deploy.yml` test job gets `timeout-minutes: 40` (no deploy-step change).

## Dependencies

- Blocks: none.
- Blocked by: none.
- Related: AE-0363 (autopilot resume runs the phase), AE-0315 (run heartbeat), AE-0412
  (public locale dates), PR #132 (hang report).

## Implementation Plan

1. Reproduce the hang, capture the stack, find the leaked task.
2. Await the heartbeat on stop; regression tests with a seeded bare-cancel check.
3. CI timeouts + faulthandler.
4. Gherkin, shared locale helper, surfaces, tests.

## QA Checklist

- [x] Security reviewed (no new input surfaces; formatting only)
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested (invalid dates, unknown locale, caller cancel, future instants)
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-17

Hang reproduced and root-caused; fix + tests; CI timeouts; locale helper and dashboard
surfaces; gates run (see dev summary).

## Files Touched

See Delta.

## Test Evidence

See `.agent/reports/AE-0417.dev-summary.md`.

## QA Report

Pending (CI decides).

## Decision Log

- 2026-10-17: **Item 1 classified "unit tests suffice"** (CLAUDE.md AE-0153): (a) no
  public/user-visible behaviour change — the heartbeat already stopped on cancel, it now
  stops *before* the run returns; CI timeouts and faulthandler are tooling; (b)
  seeded-violation proof: restoring the bare `cancel()` fails 3 of the 6 new unit tests;
  (c) affected gates: backend test, diff-cover, mutation (CI); workflow timeouts on
  backend Test & Coverage, ci-gate backend-gate, deploy test; (d) reviewer/QA sign-off
  requested on the PR.
- 2026-10-17: `stop_heartbeat` uses `asyncio.wait` instead of `suppress(CancelledError)`
  around `await task`: suppressing would also swallow a cancel of the run itself.
- 2026-10-17: no pytest-timeout (the repo does not use it, the brief says not to add the
  dependency); `faulthandler_timeout` is pytest built-in and only dumps stacks.
- 2026-10-17: timeouts sized ~2x the observed green duration so a slow runner does not
  false-fail. The mutation job is left alone: mutmut has its own per-mutant timeouts.
- 2026-10-17: the heartbeat loop moved to its own module to keep the runner under 400 lines;
  the two integration tests now patch the interval where the loop reads it.
- 2026-10-17: dashboard dates use the AE-0412 formats in local time; public pages keep UTC.
  Chat relative times use `Intl.RelativeTimeFormat` (pt "há 5 min.", en "5m ago"; "now" /
  "agora" under a minute instead of "Just now").

## Blockers

None.

## Final Summary

Pending.
