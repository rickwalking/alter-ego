# AE-0150 — Frontend: refactor top duplication hotspots (SSE hooks, carousel workflow routes) and tighten jscpd threshold

Status: Ready
Tier: T2
Priority: Medium
Type: Refactor
Area: Frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
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

- [ ] SSE handling shared between `use-sse-chat` and `use-publish-chat` (clone removed).
- [ ] Carousel workflow resume/start routes share a helper (clone removed).
- [ ] `npx jscpd src` source duplication drops below the AE-0149 threshold.
- [ ] jscpd `threshold` lowered to the new level (ratchet down) and gate green.
- [ ] No behavior change (tests pass; gates green).

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

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
