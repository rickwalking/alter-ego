# AE-0447 — Cover picker always answers 409: the workflow SSE merge drops lock_version

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Frontend
Owner: Orchestrator (Claude)
Branch: fix/ae-0447-workflow-lock-version
Created: 2026-10-21
Updated: 2026-10-21

## Goal

The publish step's "Capa (slide 1)" picker (AE-0445) switches the cover instead of always answering
"O carrossel mudou desde que você abriu esta página. Recarregue a página e tente de novo."

## Problem

Prod, 2026-10-21 09:41Z, carousel `787085ba` (POV, final review): every `PUT /api/carousels/{id}/cover` from the
page returned 409, also right after a reload. The database `lock_version` was 10 and unchanged; the same PUT with
`expected_version: 10` succeeds (verified with a read-only probe that re-picked the current photo).

Root cause: `mergeWorkflowState` (`use-editorial-workflow-utils.ts`) rebuilds the workflow state field by field on
every SSE event and never copied `lock_version`, so after the stream's connect snapshot the page had
`lock_version: undefined`. The publish page passed `workflowState.lock_version ?? 1` to the picker, so it sent 1.
Even with the merge fixed, a successful switch bumps the version and page state would go stale for the next pick.

## Scope

- `mergeWorkflowState` keeps `lock_version` (payload value, else the previous one) in both branches; the SSE
  payload type carries the optional field.
- The cover picker reads the current `lock_version` from `GET workflow/state` right before each PUT; the
  `lockVersion` prop and the `?? 1` fallback are removed from the component and the publish page.

## Non-Goals

- No backend change (the endpoint and its CAS are correct).
- Do not refactor unrelated workflow actions.

## Acceptance Criteria

- [x] A progress event or a full snapshot without `lock_version` keeps the previous `lock_version`; a snapshot with
      a new value replaces it.
- [x] A pick sends the server's current version (read right before the PUT), never page state or a guessed 1.
- [x] Existing cover-picker behaviour (progress, refresh, 409 hint, errors, keyboard) unchanged.

## Repro Steps

1. Open `/dashboard/create/<pov carousel>/publish` (completed POV carousel at final review).
2. Wait for the workflow stream to connect, pick another photo under "Capa (slide 1)".
3. Before: 409 "O carrossel mudou…" every time. After: the cover switches.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

AE-0445 (#166).

## Progress Log

### 2026-10-21 06:40

Diagnosed on prod (logs + DB + read-only API probe), fixed, tests added.
Note: the probe re-picked the CURRENT photo with version 10, which the server treated as a real switch
(slide 1 re-rendered with the same photo, lock_version 10 -> 11). No visible change.

## Files Touched

- frontend/src/modules/editorial/workspace/hooks/use-editorial-workflow-utils.ts
- frontend/src/modules/editorial/workspace/hooks/types.ts
- frontend/src/modules/publishing/distribution/hooks/use-cover-picker.ts
- frontend/src/modules/publishing/distribution/hooks/types.ts
- frontend/src/modules/publishing/distribution/components/cover-picker-section.tsx
- frontend/src/modules/publishing/distribution/components/types.ts
- frontend/src/app/dashboard/create/[id]/publish/page.tsx
- frontend/tests/features/workflow-lock-version-ae0447.feature
- tests: use-editorial-workflow-utils.test.ts, cover-picker-section.test.tsx

## Test Evidence

Targeted vitest: 3 files, 62 passed; `tsc --noEmit` clean. Gate run in the PR body.

## Final Summary

Pending merge.

## QA Report

Pending.

## Blockers

None.
