# AE-0440 — Editor workflow stream loops on 401 forever; the page looks stuck

Status: Done
Tier: T1
Priority: P1
Type: Bug
Area: Frontend
Owner: Claude (orchestrator-reported owner incident, 2026-10-20)
Agent Lane: developer → qa → release
Branch: feat/ae-0440-workflow-stream-401-loop
Kanban Card: TBD
Created: 2026-10-20
Updated: 2026-10-20

## Goal

The editor's live workflow stream never retries a dead stream forever: an expired session
goes to the session-expired login, a backend outage backs off and ends in a visible
"live updates disconnected / retry" state, and the page never presents a past phase's
progress as live work.

## Problem

Owner report, 2026-10-20: carousel `5344b6c6-1d66-4b0e-9989-93f1316f8829` looked "stuck
on image generation" in `/dashboard/create/5344b6c6…`. DB truth (read-only prod check):
`status=completed`, workflow at `final_review` awaiting the owner. The owner's tab had an
expired session: nginx/backend logs show `GET /api/carousels/5344b6c6…/workflow/stream → 401`
every ~6 s for 5+ hours (~3,000 requests) from the 03:02Z deploy on. No redirect, no
message; the page kept stale state.

### Root cause (file:line on `origin/main`, 4f811e6fd2)

- `frontend/src/modules/editorial/workspace/hooks/use-editorial-workflow-sse.ts:260-267`:
  `onerror` closed the stream, entered the polling fallback and reconnected after
  `EDITORIAL_WORKFLOW_POLL_BACKOFF_MS[0]` (5 s) **forever**. `EventSource` cannot see the
  HTTP status of a failed stream, so a 401 looked like a dropped connection.
- `:295-298`: at `awaiting_human` the polling fallback is skipped, so nothing ever
  refetched the state (and `refreshState` uses `authenticatedFetch`, which has no 401
  redirect, so polling would not have noticed the expired session either).
- Stale progress: `carousel_projects.phase_progress` is written only by the images node
  (`nodes/images.py:480`, `phase: "generating_images"`) and is never cleared; prod has it
  on 29 of 30 completed projects. `create-workflow-progress.tsx:27-37` rendered it whenever
  `loading` or `phase_status=in_progress`, whatever the current phase, so approving at
  final review (loading) or a send-back run (content in progress) showed the stale
  "Generating 4 slide images… 4/4" grid.

## Scope

- Stream error → auth probe `GET workflow/state` through `apiCall`
  (`workflow-stream-probe.ts`): a 401 runs the existing session-expired redirect
  (`redirectToLoginAfterUnauthorized` → `/auth/logout?redirect=…`, AE-0429/AE-0431) and
  never reconnects; a 403 goes to `/403` and never reconnects; a 404 disconnects; a 200
  applies the refetched state (also at `awaiting_human`) and reconnects; network/5xx back off.
- Reconnect with the whole backoff array (5 s, 10 s, 30 s, then 30 s), capped at
  `EDITORIAL_WORKFLOW_SSE_MAX_RECONNECT_ATTEMPTS = 5` in a row; then transport mode
  `disconnected` and a visible "Live updates disconnected" alert with a Retry button on
  every create step (`workflow-live-updates-disconnected.tsx`). A stream that opens resets
  the budget; a reopened stream refetches the state.
- Tab visibility regain: a live stream refetches the state; a dead stream probes and
  reconnects with a fresh budget (`use-workflow-stream-reconnect.ts`).
- Stale progress (UI side, decision below): `CreateWorkflowProgress` shows
  `phase_progress` only when its phase tag maps to the current phase
  (`PHASE_PROGRESS_TAG_TO_EDITORIAL_PHASE`: `generating_images → images`); untagged
  progress and tags that name no workflow phase still render.

### Decision: fix stale progress in the UI, not the backend

The progress column is display-only and its only writer is the images node. Clearing it
on phase completion would need a new write in the editorial transition path plus a data
backfill for the 29 existing rows (a prod write). Filtering in the one UI surface that
renders it fixes the existing rows and every future one with no prod write. The legacy
`CarouselProgress` component (`create-carousel-progress.tsx`) also takes a progress prop
but has no caller, so it is out of scope.

## Non-Goals

- Changing the backend stream endpoint, its auth, or the nginx config.
- Clearing `phase_progress` in the DB.
- Polling at `awaiting_human` (the probe after each stream error already refetches).

## Acceptance Criteria

- [x] AC1: a stream error is followed by an api-client probe; a 401 goes through the
  session-expired redirect and the stream is never reopened (no blind reconnect on auth failure).
- [x] AC2: reconnects use the whole backoff array, are capped, then show a visible
  "live updates disconnected / retry" state; Retry reopens with a fresh budget.
- [x] AC3: the state is refetched on reconnect and on tab visibility regain.
- [x] AC4: a past phase's `phase_progress` is not presented as live progress.
- [x] AC5: Gherkin + hook tests with a mocked EventSource and a 401 probe.
- [ ] AC6: frontend gates (except local mutation) green locally; CI green.

## Gherkin Scenarios

`frontend/tests/features/workflow-stream-recovery-ae0440.feature`

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None. Builds on the AE-0429/AE-0431 session-expired route.

## Progress Log

### 2026-10-20

Prod read-only check (DB row + logs from the brief), root cause in the SSE hook, fix +
Gherkin + tests. New hook tests fail 10/16 against the pre-fix hook.

## Files Touched

- `frontend/src/constants/editorial-workflow.ts`
- `frontend/src/modules/editorial/workspace/hooks/{use-editorial-workflow-sse,use-editorial-workflow,use-workflow-stream-reconnect,workflow-stream-probe,types}.ts`
- `frontend/src/app/dashboard/create/workspace/{create-workflow-panel,create-workflow-progress,workflow-live-updates-disconnected}.tsx`
- `frontend/src/i18n/locales/{en,pt}.json`
- Tests: `use-workflow-stream-reconnect.test.ts` (new), `create-workflow-progress.test.tsx`,
  `create-workflow-panel.test.tsx`, `use-editorial-workflow.test.ts`
- `frontend/tests/features/workflow-stream-recovery-ae0440.feature`

## Test Evidence

See the PR body (gate run per frontend gate, mutation deferred to CI).

## QA Report

Pending.

## Blockers

None.

## Final Summary

**Merged and closed (orchestrator, 2026-10-20).** Merged #156 (8571609, 2026-10-20), deployed in 77eca74. Incident: owner tab on 5344b6c6 had looped on 401 every 6 s since the 03:02Z deploy (~3,000 requests).
