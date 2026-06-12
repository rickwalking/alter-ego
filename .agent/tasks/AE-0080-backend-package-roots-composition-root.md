# AE-0080 — Package roots + composition-root scaffolding (bootstrap/modules/platform/legacy)

Status: Review
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
- Update `scripts/metrics/import_baseline.py` `CONTAINER_ALLOWED` (currently `api/app.py`, `api/dependencies/`) to the new `bootstrap/` composition-root paths, so the AE-0078 baseline and AE-0082 contracts stay consistent after the move.

## Non-Goals

- No moves of domain, application, or infrastructure business logic (Phase 2+).
- No route, schema, or API response changes.
- No new bounded-context code.

## Modularization Alignment (2026-06-12)

Phase 1 of the approved modularization plan (`.agent/reports/domain-modularization.options.md` §Phase 1). Scaffolding only — **no behavior moves, no schema changes, no route changes, no write redirection** (plan exit gate). The migrate-in-place delta review cleared Phase 1 (`.agent/reports/domain-modularization.delta-review.md`); the 4 residual WARNs are pre-Phase-4 (`docs/architecture/phase-0-risk-register.md`) and do not apply here. Use glossary (AE-0071) context names and ADR-0009 conventions. Composition root → `bootstrap/`; bounded contexts will later live under `modules/`; shared technical concerns under `platform/`; pre-migration coordinators under `legacy/`.

## Acceptance Criteria

- [ ] WHEN the backend is imported THE roots `bootstrap/`, `modules/`, `platform/`, `legacy/` SHALL exist, each with a documented purpose
- [ ] WHEN composition-root wiring is relocated THE domain/application/infrastructure business logic SHALL be unchanged (verified by the full suite passing AND the route snapshot below, not by visual diff alone)
- [ ] WHEN `uv run pytest` runs THE full suite SHALL pass unchanged
- [ ] WHEN the app boots THE sorted OpenAPI paths+methods SHALL equal a committed pre-change snapshot (deterministic route-equality check)
- [ ] WHEN `CONTAINER_ALLOWED` is updated to the bootstrap paths THE regenerated AE-0078 baseline SHALL show no NEW container-locator violations from the move (count unchanged)
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

- [x] Security reviewed
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-06-12

Ticket created by planner (Phase 1 epic breakdown).

## Files Touched

- bootstrap/modules/platform/legacy roots; bootstrap/app_factory.py; api/app.py shim; main.py; tests/snapshots/openapi_routes.json + test_route_snapshot.py; import_baseline.py CONTAINER_ALLOWED

## Test Evidence

```
lint-imports 8/0; mypy 407; pytest 1662 passed; route snapshot pass
```

## QA Report

✅ PASS — Phase 1 batch QA, 2 independent passes (OpenCode+Cursor) both PASS. See `.agent/reports/AE-0080.qa.md` -> `.agent/reports/phase-1.qa.md`.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
