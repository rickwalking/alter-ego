# AE-0081 — Module public-API conventions + reusable module template

Status: Review
Tier: T2
Priority: Medium
Type: Docs
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: docs/ae-0081-module-conventions
Kanban Card: TBD
Created: 2026-06-12
Updated: 2026-06-12

## Goal

Define how a bounded-context module exposes a public API (single public facade; internals private) and publish a reusable module template, so Phase 2+ modules are consistent and Import-Linter-enforceable.

## Problem

Phase 2 (Knowledge) and later phases need a documented, repeatable module shape before code is moved. Without an agreed public-API convention, modules will leak internals and the import contracts (AE-0082) cannot be written precisely.

## Scope

- Publish `docs/architecture/module-conventions.md`: per-module layout (domain/application/infrastructure/api), the public-facade rule (cross-module imports only via the module's public API), Unit-of-Work boundary placement, and naming aligned to the glossary (AE-0071).
- Provide a skeleton template (`backend/src/rag_backend/modules/_template/` or a documented example) demonstrating the convention.
- State how the convention maps to Import Linter contracts (input for AE-0082).

## Non-Goals

- No real module implementation (Phase 2).
- No code behavior change.

## Modularization Alignment (2026-06-12)

Phase 1 of the approved modularization plan (`.agent/reports/domain-modularization.options.md` §Phase 1). Scaffolding only — **no behavior moves, no schema changes, no route changes, no write redirection** (plan exit gate). The migrate-in-place delta review cleared Phase 1 (`.agent/reports/domain-modularization.delta-review.md`); the 4 residual WARNs are pre-Phase-4 (`docs/architecture/phase-0-risk-register.md`) and do not apply here. Use glossary (AE-0071) context names and ADR-0009 conventions. Conventions must match ADR-0009 (manual constructor injection, context-owned boundaries) and the glossary context names (editorial, carousel_presentation, persona, quality, publishing, knowledge, conversation, editorial_operations, identity/platform).

## Acceptance Criteria

- [ ] WHEN a developer reads `docs/architecture/module-conventions.md` THE doc SHALL define the public-facade rule, per-module layer layout, UoW boundary, and the cross-module import rule
- [ ] WHEN the template is referenced THE skeleton module SHALL exist and follow the convention
- [ ] WHEN the conventions are checked against AE-0071 THE context names SHALL resolve against the glossary with no conflicts
- [ ] THE doc SHALL state the Import Linter contract shape that AE-0082 will enforce
- [ ] WHEN `MYPYPATH=src uv run mypy -p rag_backend` runs THE skeleton template module SHALL type-check cleanly
- [ ] WHEN `uv run lint-imports` runs THE skeleton template SHALL satisfy the public-facade contract (no internal cross-module import)
- [ ] THE conventions doc SHALL provide the minimum stub AE-0082 contracts reference before they finalize (resolves the 0081->0082 ordering)

## Gherkin Scenarios

Not applicable — scaffolding/structure only; no runtime behavior change.

## Delta

### ADDED

- `docs/architecture/module-conventions.md`
- module skeleton template

### MODIFIED

- None

### REMOVED

- None

## Affected Areas

- Backend: template skeleton only
- Frontend: none
- Database: none
- API: none
- Tests: none
- Docs: module conventions
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0082 (contracts implement these conventions)
- Blocked by: none
- Related: AE-0080, AE-0070

## Implementation Plan

1. Draft module-conventions.md (layout, public facade, UoW, naming).
2. Add a skeleton template module demonstrating it.
3. Cross-link ADR-0009 + glossary; specify the contract shape for AE-0082.

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

- docs/architecture/module-conventions.md; backend/src/rag_backend/modules/_template/

## Test Evidence

```
mypy 407 clean; lint-imports 4->8 kept/0 broken; ruff clean; pytest 1662 passed
```

## QA Report

✅ PASS — Phase 1 batch QA, 2 independent passes (OpenCode+Cursor) both PASS. See `.agent/reports/AE-0081.qa.md` -> `.agent/reports/phase-1.qa.md`.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
