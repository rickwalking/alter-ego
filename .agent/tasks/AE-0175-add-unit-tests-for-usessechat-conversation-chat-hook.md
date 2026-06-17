# AE-0175 — Add unit tests for useSseChat (conversation chat hook)

Status: Review
Tier: T1
Priority: Medium
Type: Task
Area: Frontend
Owner: developer-skill
Branch: feat/ae-0152-0155-frontend-quality-epic
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Add a dedicated test suite for the `useSseChat` conversation chat hook
(`frontend/src/modules/conversation/hooks/use-sse-chat.ts`), covering the logic
unique to it that the shared hook tests don't exercise.

## Problem

Source: AE-0149-0151 QA report (`.agent/reports/AE-0149-0151.qa.md`, "Top Risks").
`useSseChat` has **no dedicated test file** (pre-existing gap). The AE-0150
refactor moved the streaming primitives into the shared, tested `useChatStream`
hook, but `useSseChat`'s own behavior is still untested:
- `mergeMessages` (dedupe of history vs optimistic by `role:content`),
- `finalizeStream` (idempotent via `finalizedRef`; query invalidation +
  optimistic clear; the `enableHistory: false` ephemeral path),
- `startNewChat` (abort + clear),
- the SOURCES / COMPLETE / ERROR event branches and `error` state,
- the `overrideConversationId` send path and the no-convId / empty-content guards.

This is the one consumer of the new shared hook without its own integration test;
`usePublishChat` has a 47-test suite. Closing this removes the residual risk
flagged by QA.

## Scope

- Add `frontend/src/modules/conversation/hooks/use-sse-chat.test.ts` (renderHook +
  a **controllable fake async SSE stream** (resolve events on demand) and a **real
  `QueryClient`** — mock only the network seam, not the behavior under test, to
  avoid locking in implementation details).
- Cover happy path (send → tokens → complete → history invalidation), the
  ephemeral `enableHistory: false` path, error/onError, SOURCES merge, dedupe in
  `mergeMessages`, `startNewChat`, and the send-guard edge cases.
- **Race / lifecycle cases (the highest-risk paths — skeptical review):**
  overlapping/double `sendMessage`, abort-before-complete, unmount-before-complete,
  history arriving DURING an optimistic stream, `finalizedRef` idempotency
  (COMPLETE + onComplete both firing), and query-invalidation ordering.

## Non-Goals

- Do not refactor `useSseChat` itself (behavior is correct; this is test-only).
- Do not change the shared `useChatStream` hook.
- Do not write pure branch-coverage tests that over-mock and assert nothing
  meaningful — race/lifecycle correctness is the goal, not a coverage number.

## Acceptance Criteria

- [x] `use-sse-chat.test.ts` exists and covers happy path, ephemeral path,
      error path, SOURCES merge, message dedupe, startNewChat, and send guards.
- [x] **Race/lifecycle cases covered** with a controllable fake stream + real
      QueryClient: overlapping sends, abort-before-complete,
      unmount-before-complete, mid-stream history arrival, `finalizedRef`
      idempotency. Tests assert observable state, not internal call counts.
- [x] Tests pass; `frontend:test` gate green.
- [x] No production behavior change.

## Repro Steps

1. `find frontend/src/modules/conversation -name 'use-sse-chat.test.*'` → no match
   (the hook is untested; only the shared `useChatStream` and `usePublishChat` are).

## Affected Areas

- [ ] Backend
- [ ] Frontend
- [ ] Tests

## Dependencies

- Related: AE-0150 (introduced the shared `useChatStream` hook this consumer uses).
- Source: `.agent/reports/AE-0149-0151.qa.md` (Top Risks).

None.

## Progress Log

### 2026-06-16 HH:mm

Ticket created.

### 2026-06-16 — Skeptical review resolved

External cold critic (`.agent/reports/AE-0172-0175.skeptical-review.md`) warned the
tests could over-mock and miss the real risk (concurrency/lifecycle). **Accepted** —
scope/ACs now mandate a controllable fake stream + real QueryClient and explicit
race cases (overlapping sends, abort/unmount-before-complete, mid-stream history,
finalizedRef idempotency), asserting observable state rather than call counts.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

PASS (wave QA) — see [AE-0172-0175.qa.md](../reports/AE-0172-0175.qa.md). 15/15 frontend gates green; integrity 0 net-new blockers; all ACs MET; 0 blocker findings.

## Blockers

None.
