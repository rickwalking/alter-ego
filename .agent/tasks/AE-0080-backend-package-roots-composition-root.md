# AE-0080 — Package roots + composition-root scaffolding (bootstrap/modules/platform/legacy)

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0080-package-roots
Kanban Card: TBD
Created: 2026-06-12
Updated: 2026-06-12

## Goal

Add the `bootstrap/`, `modules/`, `platform/`, and `legacy/` package roots under `backend/src/rag_backend/` and move ONLY composition-root responsibilities (DI container assembly / app wiring) into `bootstrap/`. No business logic moves.

## Problem

The target architecture needs physical package roots before any module can be carved out. Today wiring lives mixed with infrastructure/api. Phase 1 establishes the roots and relocates only the composition root, leaving domain/application/infrastructure logic untouched.

## Scope

- Create `backend/src/rag_backend/{bootstrap,modules,platform,legacy}/` with `__init__.py` and a module docstring/README stating each root's purpose (bootstrap=composition root; modules=bounded contexts; platform=shared technical; legacy=pre-migration coordinators).
- Move composition-root responsibilities (container assembly, app/DI wiring) into `bootstrap/` — wiring only, not business logic.
- Update imports/entrypoints so the app starts identically; keep all routes unchanged.

## Non-Goals

- No moves of domain, application, or infrastructure business logic (Phase 2+).
- No route, schema, or API response changes.
- No new bounded-context code.

## Modularization Alignment (2026-06-12)

Phase 1 of the approved modularization plan (`.agent/reports/domain-modularization.options.md` §Phase 1). Scaffolding only — **no behavior moves, no schema changes, no route changes, no write redirection** (plan exit gate). The migrate-in-place delta review cleared Phase 1 (`.agent/reports/domain-modularization.delta-review.md`); the 4 residual WARNs are pre-Phase-4 (`docs/architecture/phase-0-risk-register.md`) and do not apply here. Use glossary (AE-0071) context names and ADR-0009 conventions. Composition root → `bootstrap/`; bounded contexts will later live under `modules/`; shared technical concerns under `platform/`; pre-migration coordinators under `legacy/`.

## Acceptance Criteria

- [ ] WHEN the backend is imported THE roots `bootstrap/`, `modules/`, `platform/`, `legacy/` SHALL exist, each with a documented purpose
- [ ] WHEN composition-root wiring is relocated THE `git diff` SHALL show only moves/wiring, not changed business logic
- [ ] WHEN `uv run pytest` runs THE full suite SHALL pass unchanged
- [ ] WHEN the app boots THE OpenAPI schema / routes SHALL be byte-identical to pre-change
- [ ] WHEN `MYPYPATH=src uv run mypy -p rag_backend` runs THE type check SHALL pass
- [ ] WHEN `uv run lint-imports` runs THE existing contracts SHALL still pass (no new violations)

## Gherkin Scenarios

Not applicable — scaffolding/structure only; no runtime behavior change.

## Delta

### ADDED

- `backend/src/rag_backend/bootstrap/` (+ __init__, README)
- `backend/src/rag_backend/modules/` (+ __init__, README)
- `backend/src/rag_backend/platform/` (+ __init__, README)
- `backend/src/rag_backend/legacy/` (+ __init__, README)

### MODIFIED

- composition-root / app-assembly / container-wiring modules relocated into `bootstrap/`
- entrypoint imports updated to the new wiring location

### REMOVED

- None

## Affected Areas

- Backend: yes (package roots + composition root)
- Frontend: none
- Database: none
- API: none (routes unchanged)
- Tests: existing suite must stay green
- Docs: per-root READMEs
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0082 (import contracts target these roots)
- Blocked by: none (Phase 0 complete)
- Related: AE-0081, AE-0070

## Implementation Plan

1. Create the four roots with __init__.py + purpose docstring/README.
2. Identify composition-root code (container/app assembly) and move it into bootstrap/.
3. Fix imports/entrypoints; run app to confirm routes unchanged.
4. Run pytest, mypy, lint-imports; confirm green.

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
