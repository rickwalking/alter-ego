# AE-0095 — Knowledge import contract + exit-gate enforcement + template doc

Status: Review
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0095-knowledge-exit-gate
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Add an Import Linter contract enforcing the Phase 2 exit gate (no SQLAlchemy/FastAPI/Pinecone/global container in the knowledge application layer), ratchet the baseline accordingly, and document the knowledge module as the reusable template.

## Problem

The exit gate requires the new module's application layer to be free of framework/vendor/container imports. This must be CI-enforced (building on AE-0082) and the proven pattern documented for Phases 3-8.

## Scope

- Add an Import Linter contract: `modules.knowledge.application` (and domain) forbidden from importing `sqlalchemy`, `fastapi`, Pinecone SDK, and `infrastructure.container`/`get_container`.
- ALSO add the knowledge-public-facade contract (mirror module-conventions §7a / `_template`): cross-module callers (agents, api, other modules) import ONLY `rag_backend.modules.knowledge`, not internals.
- Regenerate the AE-0082 baseline so the cleaned knowledge module ratchets DOWN (never up); keep `--check` green.
- Update `docs/architecture/module-conventions.md` with the knowledge module as the worked example / reusable template.
- Confirm the exit-gate contract via a demonstrated new-violation failure.

## Non-Goals

- No weakening of existing contracts.
- No behavior change.

## Modularization Alignment (2026-06-15)

Phase 2 of the modularization plan (`.agent/reports/domain-modularization.options.md` §Phase 2). **Behavior-preserving extraction** — `/api/documents` and `/api/search` stay byte-identical; NO renames (Phase 4+). Builds on Phase 1 (PR #15): follow `docs/architecture/module-conventions.md` (AE-0081) + `modules/_template/`; satisfy the AE-0082 import contracts; compose via `bootstrap/` (no `get_container()` in module application code). Risk-register F1-F4 are Phase 4+ and do not apply (additive only). Caps Phase 2; the contract + template are what later phases copy.

## Acceptance Criteria

- [ ] AN Import Linter contract SHALL forbid the knowledge application/domain layer from importing SQLAlchemy, FastAPI, Pinecone, or the global container; `lint-imports` passes (kept)
- [ ] WHEN new knowledge app code imports a forbidden dependency THE contract SHALL fail (demonstrated, reverted)
- [ ] THE knowledge-public-facade contract SHALL forbid cross-module imports of knowledge internals (agents/api import only the facade); demonstrated by a reverted internal-import violation
- [ ] THE AE-0082 baseline/`--check` SHALL be updated so knowledge counts ratchet down, not up (still PASS)
- [ ] `docs/architecture/module-conventions.md` SHALL document the knowledge module as the reusable template
- [ ] mypy strict + full suite + all Phase-1 ratchets green

## Gherkin Scenarios

```gherkin
Feature: Knowledge module boundary enforced

  Scenario: new framework import in the module is blocked
    Given the knowledge application layer
    When a new `import sqlalchemy` is added there
    Then lint-imports fails the knowledge contract
```

## Delta

### ADDED

- Import Linter knowledge contract
- module-conventions.md worked example

### MODIFIED

- backend/.importlinter
- scripts/metrics/import_baseline.py baseline
- docs/architecture/module-conventions.md

### REMOVED

- None

## Affected Areas

- Backend: import contract
- Frontend: none
- Database: none
- API: none
- Tests: contract demo
- Docs: reusable template
- Prompts/LLM: none
- Observability: none
- Deployment: no

## Dependencies

- Blocks: none
- Blocked by: AE-0092, AE-0093
- Related: AE-0082, AE-0085, AE-0081

## Implementation Plan

1. Add the knowledge boundary contract.
2. Ratchet the baseline down; verify --check.
3. Document the template; demo a new-violation failure.

## QA Checklist

- [x] Security reviewed
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 2 breakdown).

## Files Touched

- backend/.importlinter (2 new contracts); scripts/metrics/import_baseline.py; docs/architecture/module-conventions.md

## Test Evidence

```
gates.sh backend: 13 PASS / 0 FAIL / 4 SKIP(DB); check-integrity: 0 net-new blockers
mypy 424; lint-imports 10/0; full suite 1757 passed; snapshot diff=0
```

## QA Report

✅ PASS — Phase 2 batch QA (gates.sh + check-integrity reproduced), 2 passes WARN→PASS. See `.agent/reports/AE-0095.qa.md` -> `.agent/reports/phase-2.qa.md`.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
