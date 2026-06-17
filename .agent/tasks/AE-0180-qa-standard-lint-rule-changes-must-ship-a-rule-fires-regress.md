# AE-0180 — QA standard: lint-rule changes must ship a rule-fires regression test

Status: Intake
Tier: T2
Priority: Medium
Type: Quality
Area: Cross-cutting
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-17
Updated: 2026-06-17

## Goal

Codify as a QA standard that any change introducing or promoting a static
analysis rule (ESLint, ruff, a custom `scripts/` checker) ships a regression test
that proves the rule FIRES on a seeded violation — not just that the current tree
passes.

## Problem

Kaizen learning K2 from the Phase 8 Class B QA wave. AE-0166 claimed several rules
were "seeded-verified" as errors, but only the `use-client` check had a committed
test; the `fetch`-in-`useEffect` and `no-console` claims rested on transient manual
probes. A QA reviewer flagged this as an unverifiable claim, and the related H1
defect (a rule silently downgraded) would have been caught immediately by such a
test. "Passes on the real tree" proves nothing about whether the rule actually
catches the thing it targets.

## Scope

- Add the standard to `docs/guides/qa-checkpoints.md` and the QA agent's
  code-quality dimension: "rule added/promoted ⇒ a test asserting it errors on a
  seeded violation."
- Reference the pattern exemplars: `frontend/src/scripts/use-client.test.ts` and
  `eslint-fetch-rule.test.ts`.

## Non-Goals

- Not retroactively backfilling tests for every pre-existing rule (separate, larger).
- Not a code change to the rules themselves.

## Acceptance Criteria

- [ ] `docs/guides/qa-checkpoints.md` documents the rule-fires-test requirement.
- [ ] QA agent code-quality checklist includes it.
- [ ] Linked from `CLAUDE.md`/`frontend/CLAUDE.md` testing section.

## Gherkin Scenarios

```gherkin
Feature: ...

  Scenario: ...
    Given ...
    When ...
    Then ...
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

### 2026-06-17 HH:mm

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
