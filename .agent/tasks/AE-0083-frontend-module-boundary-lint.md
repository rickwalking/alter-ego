# AE-0083 — Frontend module-boundary lint rules

Status: Review
Tier: T2
Priority: Medium
Type: Task
Area: Frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0083-frontend-boundary-lint
Kanban Card: TBD
Created: 2026-06-12
Updated: 2026-06-12

## Goal

Add ESLint rules that forbid cross-feature internal imports (feature A importing feature B's internals), baselining existing violations as warnings and blocking NEW ones — mirroring the backend import ratchet. Today only `app/**` imports are guarded.

## Problem

The frontend has no cross-feature boundary enforcement; `features/*` freely import each other's internals, which will fight the modular target. Phase 1 adds the guard before Phase 7 frontend alignment, grandfathering current violations.

## Scope

- Add ESLint config (`no-restricted-imports` or an eslint-plugin-boundaries setup) forbidding `features/A/**` from importing `features/B/**` internals; allow shared (`components/`, `lib/`, `constants/`, `i18n/`) and a feature's own public entry.
- Baseline current cross-feature imports (warn / allowlist) so the build is not newly broken; NEW cross-feature imports error.
- Keep the existing `app/**` import guard intact.

## Non-Goals

- No moving/refactoring existing feature code to remove violations (Phase 7).
- No component behavior change.

## Modularization Alignment (2026-06-12)

Phase 1 of the approved modularization plan (`.agent/reports/domain-modularization.options.md` §Phase 1). Scaffolding only — **no behavior moves, no schema changes, no route changes, no write redirection** (plan exit gate). The migrate-in-place delta review cleared Phase 1 (`.agent/reports/domain-modularization.delta-review.md`); the 4 residual WARNs are pre-Phase-4 (`docs/architecture/phase-0-risk-register.md`) and do not apply here. Use glossary (AE-0071) context names and ADR-0009 conventions. Mirrors the backend ratchet philosophy (AE-0082): grandfather existing, block new. Aligns with the eventual frontend context names (AE-0071).

## Acceptance Criteria

- [ ] WHEN `npm run lint` runs THE config SHALL flag a NEW cross-feature internal import as an error
- [ ] WHEN an existing (baselined) cross-feature import is present THE lint SHALL NOT newly fail the build, using a COMMITTED, reproducibly-generated baseline/allowlist (documented generation command — not hand-edited)
- [ ] THE cross-feature violation count SHALL be recorded in the committed baseline and the lint SHALL fail if the count rises above it
- [ ] WHEN a new cross-feature import is added and then removed THE error SHALL appear then clear (demonstrated)
- [ ] THE existing `app/**` import guard SHALL remain enforced
- [ ] WHEN `npm run lint` and `npm run typecheck` run THE checks SHALL pass on the current tree

## Gherkin Scenarios

```gherkin
Feature: Frontend feature boundaries

  Scenario: new cross-feature import blocked
    Given features/create importing features/publish internals
    When npm run lint runs
    Then it errors naming the restricted import

  Scenario: shared imports allowed
    Given a feature importing components/atoms or lib
    When npm run lint runs
    Then no boundary error is raised
```

## Delta

### ADDED

- ESLint boundary rule config (+ baseline allowlist if needed)

### MODIFIED

- `frontend/eslint.config.*` — add cross-feature boundary rule

### REMOVED

- None

## Affected Areas

- Backend: none
- Frontend: eslint boundary rules
- Database: none
- API: none
- Tests: lint demonstration
- Docs: rule rationale
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: none
- Blocked by: none
- Related: AE-0082 (parallel ratchet), AE-0047

## Implementation Plan

1. Choose mechanism (no-restricted-imports vs boundaries plugin).
2. Encode feature→feature internal ban; allow shared layers + own public entry.
3. Baseline existing violations; prove a new one errors.
4. Run lint + typecheck.

## QA Checklist

- [x] Security reviewed
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-06-12

Ticket created by planner (Phase 1 epic breakdown).

## Files Touched

- frontend/scripts/feature-boundary*.mjs + check/generate; feature-boundary-baseline.json (23); eslint.config.mjs; package.json

## Test Evidence

```
npm run lint OK (23 grandfathered, 0 new); typecheck clean; new-violation + app/** guard demonstrated
```

## QA Report

✅ PASS — Phase 1 batch QA, 2 independent passes (OpenCode+Cursor) both PASS. See `.agent/reports/AE-0083.qa.md` -> `.agent/reports/phase-1.qa.md`.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
