# AE-0077 — Re-measure frontend baseline and re-publish the estimate

Status: Ready
Tier: T2
Priority: Medium
Type: Docs
Area: Frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: docs/ae-0077-frontend-baseline
Kanban Card: TBD
Created: 2026-06-12
Updated: 2026-06-12

## Goal

A reproducible frontend baseline measurement with documented methodology,
and the modularization estimate re-published with a confidence range.

## Problem

The research report's frontend numbers (406 files / 41,638 lines; 15,036
feature lines) did not reproduce on 2026-06-12 (~305 non-test files /
~25,700 lines; ~6,100 feature lines). The 12-22 week estimate is bracketed
±25% until a methodology-documented baseline replaces them.

## Scope

- A measurement script or documented command set that reports, for
  `frontend/src`: total TS/TSX files and lines, split by
  production / test / stories, and per-feature totals for `create`,
  `carousel`, `publish`, `blog`, `workflow` (plus the rest of `features/`).
- Equivalent backend summary (files, lines, carousel services subtotal) so
  both baselines share one method.
- Publish `.agent/reports/modularization-baseline-2026-06.md` with the
  numbers, the exact commands, and inclusion/exclusion rules.
- Update `.agent/reports/domain-modularization.options.md`: append a
  dated "superseded by baseline 2026-06" note next to the ±25%
  preliminary bracket (do not delete it — the bracket is round-2 review
  closure evidence) and state the revised estimate with its confidence
  range; update the research report's correction callout to point at the
  new baseline.

## Non-Goals

- No estimate methodology beyond line/file counts (no COCOMO-style models).
- No changes to phase scopes (only the numbers and confidence range).

## Acceptance Criteria

- [ ] `.agent/reports/modularization-baseline-2026-06.md` exists with
      every number traceable to a copy-pasteable command
- [ ] Running the documented commands twice yields identical output
      (deterministic; no timestamps in the measured output)
- [ ] Production, test, and story code are counted separately with the
      classification rules written down
- [ ] Per-feature totals exist for all `frontend/src/features/*` children
- [ ] `domain-modularization.options.md` effort section cites the new
      baseline and states the revised estimate with an explicit confidence
      range via an appended superseded-note (the original ±25% bracket
      text remains in place as review-trail evidence)
- [ ] The research report's correction callouts link to the new baseline
      file

## Gherkin Scenarios

Not applicable — measurement and documentation only; no runtime behavior.

## Delta

### ADDED

- `.agent/reports/modularization-baseline-2026-06.md`
- Measurement commands (documented inline or as a small script under
  `scripts/`)

### MODIFIED

- `.agent/reports/domain-modularization.options.md` (estimate section)
- `.agent/reports/domain-modularization.research.md` (correction links)

### REMOVED

- None

## Affected Areas

- Backend: counted, not changed
- Frontend: counted, not changed
- Database: none
- API: none
- Tests: none
- Docs: baseline report + plan updates
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: final estimate publication (epic AE-0070 closure)
- Blocked by: none
- Related: AE-0070

## Implementation Plan

1. Define classification rules (test = `*.test.*`/`__tests__`/`src/test`;
   stories = `*.stories.*`; rest = production).
2. Script the counts; run twice; record output.
3. Update both plan documents.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-12 00:00

Ticket created by planner.

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
