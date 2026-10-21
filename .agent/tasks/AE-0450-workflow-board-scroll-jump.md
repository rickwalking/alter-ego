# AE-0450 — Workflow board: the page jumps back to the top on every refresh

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Frontend
Owner: Worker (Claude)
Branch: fix/ae-0450-workflow-scroll-jump
Created: 2026-10-21
Updated: 2026-10-21

## Goal

A signed-in owner can scroll and read `/dashboard/workflow` without the page snapping back to the top.

## Problem

Prod, 2026-10-21 23:41Z, QA admin account, read-only: scrolled to the bottom of `/dashboard/workflow`
(`scrollY` 1848, document height 2568). At every `GET /api/workflow-board` poll (every 15 s) the document
height dropped to 720 (viewport height), a spinner showed, and `scrollY` was 0 afterwards. Evidence:
`~/alter-ego-qa/2026-10-21-wave/ae0450/board-trace.json` and screenshots.

`/dashboard/create/<id>` (carousel workspace) was checked the same way for 45 s: no DOM removals, scroll kept.

Root cause: `useWorkflowKanban.fetchBoard` set `loading` to true on every poll and window-focus refetch, and
the page rendered the board only when `!loading && !error`. Each refresh unmounted the whole board, the page
collapsed to the spinner's height, and the browser clamped the scroll to 0. A failed refresh did the same
(the board was hidden behind the error).

## Scope

- `useWorkflowKanban` reports `loading` only until the first board arrives; refetches update data in place.
- The page keeps the loaded board mounted while refetching and when a refresh fails (error + retry shown
  above it).

## Non-Goals

- No change to the poll interval or the focus refetch.
- No migration of the hook to TanStack Query.

## Acceptance Criteria

- [x] A poll refresh keeps the same board DOM nodes and shows no spinner; new data appears in place.
- [x] A focus refresh keeps the same board DOM nodes.
- [x] A failed refresh shows the error and retry and keeps the last board mounted.
- [x] The first load still shows the spinner and no board.

## Repro Steps

1. Sign in, open `/dashboard/workflow`, scroll down.
2. Wait up to 15 s (or switch tabs and back).
3. Before: the board flashes to a spinner and the page is back at the top. After: the page stays put.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-21 23:50

Reproduced on prod (read-only), root-caused, fixed, tests added (3 of 4 fail on main, all pass with the fix).

## Files Touched

- frontend/src/modules/editorial/workflow/hooks/use-workflow-kanban.ts
- frontend/src/app/dashboard/workflow/page.tsx
- frontend/src/app/dashboard/workflow/page.test.tsx
- frontend/tests/features/workflow-board-poll-keeps-scroll-ae0450.feature

## Test Evidence

Targeted vitest: 1 file, 4 passed. Gate run in the PR body.

## Final Summary

Pending merge.

## QA Report

Pending.

## Blockers

None.
