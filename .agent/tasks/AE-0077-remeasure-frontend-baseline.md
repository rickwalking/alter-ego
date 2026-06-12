# AE-0077 — Re-measure frontend baseline and re-publish the estimate

Status: Dev Complete
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

- [x] `.agent/reports/modularization-baseline-2026-06.md` exists with
      every number traceable to a copy-pasteable command
- [x] Running the documented commands twice yields identical output
      (deterministic; no timestamps in the measured output)
- [x] Production, test, and story code are counted separately with the
      classification rules written down
- [x] Per-feature totals exist for all `frontend/src/features/*` children
- [x] `domain-modularization.options.md` effort section cites the new
      baseline and states the revised estimate with an explicit confidence
      range via an appended superseded-note (the original ±25% bracket
      text remains in place as review-trail evidence)
- [x] The research report's correction callouts link to the new baseline
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

### 2026-06-12 (development)

Implemented on docs/ae-0077-frontend-baseline. Script deterministic
(verified by double-run diff).

## Files Touched

- `scripts/metrics/baseline_loc.sh` (new, executable)
- `.agent/reports/modularization-baseline-2026-06.md` (new)
- `.agent/reports/domain-modularization.options.md` (superseded-note appended; revised estimate 11-21 ew ±15%)
- `.agent/reports/domain-modularization.research.md` (correction callouts link the baseline)

## Test Evidence

```bash
./scripts/metrics/baseline_loc.sh  # run twice, diff -q → byte-identical
```

Frontend prod 300 files / 25,403 lines; tests 74/15,867; stories 33/566;
five features 6,119 prod lines; backend 368/44,756; carousel services
72/12,405. Discrepancy root-caused: research counted all classes
(407/41,836 ≈ its 406/41,638).

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Reproducible baseline published with documented classification rules;
original research numbers reconciled as a classification omission
(tests+stories included), not a measurement error. Estimate re-issued:
11-21 engineer-weeks at ±15% confidence; the ±25% bracket retained as
review-trail evidence. Phase 7 sizing confirmed.
