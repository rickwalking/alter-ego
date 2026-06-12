# AE-0085 — CI architecture reports + violation ratchets

Status: Ready
Tier: T2
Priority: Medium
Type: Task
Area: CI/DevOps
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0085-arch-reports-ratchets
Kanban Card: TBD
Created: 2026-06-12
Updated: 2026-06-12

## Goal

Emit an architecture report in CI (import-violation counts, layer adherence) and ratchet it: fail when the violation count rises above the committed baseline, consuming the AE-0082 contracts/baseline.

## Problem

Once exact import contracts + a baseline exist (AE-0082), CI should surface architecture health and prevent regressions. Today there is no architecture report or ratchet beyond pass/fail lint-imports.

## Scope

- Add a CI step producing an architecture report: current import-violation count vs the committed AE-0078/AE-0082 baseline, plus layer/module adherence summary.
- Ratchet: fail when the violation count exceeds baseline; pass at or below (and update baseline downward when violations are retired).
- Wire into the existing gates; no new workflow sprawl.

## Non-Goals

- No auto-fixing of violations.
- No behavior/route changes.

## Modularization Alignment (2026-06-12)

Phase 1 of the approved modularization plan (`.agent/reports/domain-modularization.options.md` §Phase 1). Scaffolding only — **no behavior moves, no schema changes, no route changes, no write redirection** (plan exit gate). The migrate-in-place delta review cleared Phase 1 (`.agent/reports/domain-modularization.delta-review.md`); the 4 residual WARNs are pre-Phase-4 (`docs/architecture/phase-0-risk-register.md`) and do not apply here. Use glossary (AE-0071) context names and ADR-0009 conventions. Implements the plan's 'CI architecture reports and violation ratchets' deliverable; depends on AE-0082's generated baseline. Success metric: zero NEW global-layer violations.

## Acceptance Criteria

- [ ] WHEN CI runs THE pipeline SHALL emit an architecture report comparing current import violations to the committed baseline
- [ ] WHEN the import-violation count exceeds the baseline THE ratchet SHALL fail the build
- [ ] WHEN violations are at or below baseline THE ratchet SHALL pass
- [ ] WHEN violations are retired below baseline THE process SHALL allow ratcheting the baseline down (documented)
- [ ] THE ratchet SHALL consume the AE-0082 generated baseline (single source of truth)

## Gherkin Scenarios

```gherkin
Feature: Architecture ratchet

  Scenario: regression fails
    Given the committed import-violation baseline
    When a PR raises the violation count above baseline
    Then CI fails with the architecture report

  Scenario: at-or-below baseline passes
    Given no new violations
    When CI runs
    Then the ratchet passes
```

## Delta

### ADDED

- CI architecture-report + ratchet step
- report artifact format

### MODIFIED

- existing CI workflow (add report+ratchet)
- docs/guides/qa-checkpoints.md (gate description)

### REMOVED

- None

## Affected Areas

- Backend: none (CI only)
- Frontend: none
- Database: none
- API: none
- Tests: ratchet demonstration
- Docs: gate description
- Prompts/LLM: none
- Observability: none
- Deployment: no

## Dependencies

- Blocks: none
- Blocked by: AE-0082
- Related: AE-0078, AE-0049

## Implementation Plan

1. Build the report (violation count vs baseline + adherence summary).
2. Add the ratchet comparison; fail on regression.
3. Document baseline-down procedure; wire into existing gates.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-12

Ticket created by planner (Phase 1 epic breakdown).

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
