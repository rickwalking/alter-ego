# AE-0155 — Add unit tests for useSseChat (conversation chat hook)

Status: Intake
Tier: T1
Priority: Medium
Type: Task
Area: Frontend
Owner: Unassigned
Branch: TBD
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
  mocked `streamSseEvents` / `useConversationMessages` / QueryClient, mirroring
  `use-publish-chat.test.ts`).
- Cover happy path (send → tokens → complete → history invalidation), the
  ephemeral `enableHistory: false` path, error/onError, SOURCES merge, dedupe in
  `mergeMessages`, `startNewChat`, and the send-guard edge cases.

## Non-Goals

- Do not refactor `useSseChat` itself (behavior is correct; this is test-only).
- Do not change the shared `useChatStream` hook.

## Acceptance Criteria

- [ ] `use-sse-chat.test.ts` exists and covers happy path, ephemeral path,
      error path, SOURCES merge, message dedupe, startNewChat, and send guards.
- [ ] Tests pass; `frontend:test` gate green.
- [ ] No production behavior change.

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

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
