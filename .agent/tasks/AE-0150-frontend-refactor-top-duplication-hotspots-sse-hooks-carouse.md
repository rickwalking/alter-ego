# AE-0150 — Frontend: refactor top duplication hotspots (SSE hooks, carousel workflow routes) and tighten jscpd threshold

Status: Review
Tier: T2
Priority: Medium
Type: Refactor
Area: Frontend
Owner: developer-skill
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0149-0151-frontend-duplication-gate
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Pay down the existing frontend source duplication so the jscpd threshold
(AE-0149) can be ratcheted down toward ~1%.

## Problem

Source: kaizen analysis (`.agent/reports/kaizen-jscpd.plan.md`). The measured
1.94% source duplication concentrates in a few hotspots:
- SSE handling duplicated across `modules/conversation/hooks/use-sse-chat.ts` and
  `modules/publishing/distribution/hooks/use-publish-chat.ts` (~47 lines each).
- Carousel workflow API routes `app/api/carousels/[id]/workflow/resume/route.ts`
  and `.../start/route.ts` (~43 lines each).
- `lib/api-client.ts` (72), `app/(public)/(marketing)/page.tsx` (137).

## Scope

- Extract shared SSE stream-handling into a reusable hook/util used by both chat hooks.
- Extract the common carousel-workflow route handler logic (resume/start) into a shared helper.
- De-duplicate `api-client.ts` and the marketing page where it improves clarity.
- Lower the jscpd `threshold` in `.jscpd.json` to the new (lower) measured level.

## Non-Goals

- Over-DRYing: do not couple unrelated code just to cut clones (readability wins).
- Test-file duplication (out of scope; advisory only — AE-0151).

## Acceptance Criteria

- [x] SSE handling shared between `use-sse-chat` and `use-publish-chat` (clone removed — jscpd reports 0 clones between the two hooks). Extracted `src/lib/sse-chat-stream.ts` (pure helpers: `createOptimisticUserMessage`, `beginStream`, `appendStreamToken`, `resetStreamRefs`) + `src/lib/use-chat-stream.ts` (`useChatStream` hook owning streaming state). Also de-duped `src/lib/api-client.ts` (`fetchWithCredentials` + `throwIfErrorResponse`).
- [x] Carousel workflow resume/start routes share a helper (`_lib/proxy-workflow-action.ts`; both clones removed).
- [x] `npx jscpd src` source duplication dropped 1.45% → **1.08%** (below the AE-0149 threshold of 2).
- [x] jscpd `threshold` lowered 2 → **1.2** (ratchet down) and gate green.
- [x] No behavior change: typecheck + eslint clean; use-publish-chat (47) + api-client tests pass; all 14 frontend gates PASS. New unit tests for the extracted helpers/hook.

### Note (minor behavior improvement)

`useChatStream` aborts the in-flight stream on unmount for BOTH hooks. `usePublishChat`
already did this; `useSseChat` did not — it now gets the same defensive cleanup
(prevents state updates after unmount). No user-facing behavior change.

## Gherkin Scenarios

```gherkin
Feature: Reduce frontend source duplication

  Scenario: Shared SSE logic removes the clone
    Given use-sse-chat and use-publish-chat duplicated SSE handling
    When the shared handler is extracted and both import it
    Then jscpd reports the clone resolved and behavior is unchanged
```

## Delta

### ADDED

- ...

### MODIFIED

- ...

### REMOVED

- ...

## Affected Areas

- Backend:
- Frontend:
- Database:
- API:
- Tests:
- Docs:
- Prompts/LLM:
- Observability:
- Deployment:

## Dependencies

- Blocks:
- Blocked by:
- Related:

## Implementation Plan

1. ...

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-16 HH:mm

Ticket created.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

PASS (wave QA) — see [AE-0149-0151.qa.md](../reports/AE-0149-0151.qa.md). 14/14 frontend gates green; integrity 0 net-new blockers; all ACs verified MET; 0 blocker findings.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
