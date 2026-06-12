# AE-0082 — Import Linter exact contracts + generated baseline exception list

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0082-import-contracts
Kanban Card: TBD
Created: 2026-06-12
Updated: 2026-06-12

## Goal

Replace the wildcard exemptions in `backend/.importlinter` with exact layered contracts plus a baseline exception list **generated** from AE-0078's recorded violations, so existing violations are grandfathered but any NEW global-layer/cross-module violation fails CI.

## Problem

Today `backend/.importlinter` uses wildcard ignores that hide all violations (AE-0049 deliberately did not touch it; AE-0078 recorded the baseline first). Phase 1 must convert those wildcards into exact contracts + a generated exception list so the boundary becomes a ratchet, not a blanket pass.

## Scope

- Generate the baseline exception list from `scripts/metrics/import_baseline.py` (AE-0078) — documented, reproducible command; not hand-curated.
- Replace wildcard exemptions in `backend/.importlinter` with exact contracts: layered (domain < application < infrastructure/api), modules independent (cross-module only via public facade per AE-0081), and no container/service-locator access from application code.
- Ensure `lint-imports` passes on the current tree with the generated exceptions (existing violations grandfathered).
- Cover **all six AE-0078 baseline categories**, not just import module-pairs: the four import layer/module-pair categories PLUS `get_container()` service-locator sites (baseline=26) and adapter `.commit()` sites (baseline=9). Where Import Linter cannot express a category (locator, commit), add a complementary `import_baseline.py`-based check so every category is ratcheted.
- Commit canonical baseline numbers in a single source-of-truth artifact recording, per section: runtime unique-module-pairs, type-checking-only pairs, `get_container()` hits, `.commit()` hits — pinned to the committed AE-0078 artifact (reference its path/commit; AE-0078 is in Review, may not merge before Wave B).

## Non-Goals

- No code refactors to FIX existing violations (later phases retire them via the ratchet).
- No behavior/route/schema changes.

## Modularization Alignment (2026-06-12)

Phase 1 of the approved modularization plan (`.agent/reports/domain-modularization.options.md` §Phase 1). Scaffolding only — **no behavior moves, no schema changes, no route changes, no write redirection** (plan exit gate). The migrate-in-place delta review cleared Phase 1 (`.agent/reports/domain-modularization.delta-review.md`); the 4 residual WARNs are pre-Phase-4 (`docs/architecture/phase-0-risk-register.md`) and do not apply here. Use glossary (AE-0071) context names and ADR-0009 conventions. Targets the AE-0080 package roots and AE-0081 conventions. The exception list is generated from the AE-0078 baseline so the count can only ratchet DOWN; new violations fail.

## Acceptance Criteria

- [ ] WHEN `uv run lint-imports` runs THE contracts SHALL pass with the generated baseline exception list AND no wildcard exemptions SHALL remain in `backend/.importlinter`
- [ ] WHEN a NEW cross-layer or cross-module (non-facade) import is introduced THE contract SHALL fail (demonstrated by a temporary violation reverted in the same PR)
- [ ] WHEN a NEW `get_container()` call is added in application/domain code THE category check SHALL fail (ratchet covers locator sites, baseline=26)
- [ ] WHEN a NEW adapter `.commit()` is added THE category check SHALL fail (ratchet covers commit sites, baseline=9)
- [ ] THE comparison SHALL be field-exact per the AE-0078 artifact: per section, runtime unique-module-pairs, type-checking-only pairs, `get_container()` hits, and `.commit()` hits are each compared; counts may only stay equal or decrease, never increase
- [ ] WHEN the baseline is regenerated THE command SHALL be documented and reproducible from `scripts/metrics/import_baseline.py`, reading the committed canonical numbers (pinned to the AE-0078 artifact)
- [ ] WHEN `uv run pytest` runs THE suite SHALL pass

## Gherkin Scenarios

```gherkin
Feature: Import boundaries are ratcheted

  Scenario: existing violations are grandfathered
    Given the generated baseline exception list from AE-0078
    When lint-imports runs on the current tree
    Then it passes with zero wildcard exemptions

  Scenario: a new violation is blocked
    Given a new application-layer import of the global container
    When lint-imports runs
    Then it fails naming the offending import
```

## Delta

### ADDED

- generated baseline exception list (committed)

### MODIFIED

- `backend/.importlinter` — wildcards replaced with exact contracts + exception list

### REMOVED

- wildcard exemptions in `backend/.importlinter`

## Affected Areas

- Backend: import contracts config
- Frontend: none
- Database: none
- API: none
- Tests: a transient new-violation check
- Docs: regeneration command
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0085 (ratchet/report consumes these contracts)
- Blocked by: AE-0080 (package roots); AE-0081 (conventions inform contract shape); AE-0078 (baseline — pin to its committed artifact since it is in Review)
- Related: AE-0081, AE-0049

## Implementation Plan

1. Regenerate the violation baseline via import_baseline.py and commit the exception list.
2. Rewrite backend/.importlinter: exact layered + module-independence + no-container contracts.
3. Confirm lint-imports passes; add+revert a temporary violation to prove new ones fail.
4. Run pytest.

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
