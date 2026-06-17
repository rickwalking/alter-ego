# AE-0180 — QA standard: lint-rule changes must ship a rule-fires regression test

Status: Dev Complete
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

- [x] `docs/guides/qa-checkpoints.md` documents the rule-fires-test requirement
      (new "Rule-fires regression test standard (AE-0180)" section under Code Quality,
      with exemplar table; K2 heuristic row now links to it instead of forward-ref).
- [x] QA agent code-quality checklist includes it (Subagent 2 — Code Quality, new
      rule-fires checklist item marking a rule-add-without-test as a 🔴 Blocker).
- [x] Linked from root `CLAUDE.md` and `frontend/CLAUDE.md` testing sections.

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

- `docs/guides/qa-checkpoints.md` — new "Rule-fires regression test standard (AE-0180)"
  section + K2 heuristic row now links to it.
- `skills/delivery/qa-agent/SKILL.md` — Subagent 2 (Code Quality) rule-fires checklist item.
- `CLAUDE.md` / `frontend/CLAUDE.md` — testing-section bullets linking the standard.

## Test Evidence

Docs/process ticket — no behavior change, no gate added (per AE-0153 the
CI/config/tooling unit-test substitution does not apply because there is no new
rule or gate here; this codifies the *standard* for other tickets). Verification:

```bash
$ grep -n "rule-fires-regression-test-standard-ae-0180" CLAUDE.md frontend/CLAUDE.md  # both link the anchor
$ grep -n "## Rule-fires regression test standard (AE-0180)" docs/guides/qa-checkpoints.md  # section present
```
The standard is dogfooded by AE-0179's tests (seeded-violation + allow-list pass).

## QA Report

Pending.

## Decision Log

- No gate change: process/standard codification, not a new checker. Per AE-0153,
  a docs-only ticket with no user-visible behavior change substitutes link/anchor
  verification for a `.feature`.

## Blockers

None.

## Final Summary

Pending.
