# AE-0141 — OpenAPI/Zod schema-drift check (frontend <-> backend)

Status: Review
Tier: T2
Priority: High
Type: Task
Area: Frontend/CI
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0141-openapi-zod-schema-drift-check
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Add a schema-drift check comparing the frontend Zod schemas against the backend OpenAPI. PRECONDITION: no OpenAPI artifact exists in the repo today (only test_route_snapshot.py), so this ticket FIRST adds a small read-only export script that dumps the FastAPI `app.openapi()` to a committed artifact (e.g. docs/architecture/openapi.json) — a generator script, not a behavior change to the app — then the drift check diffs the frontend Zod schemas against that artifact; advisory first, then blocking once clean.

## Problem

Today `frontend/src/features/**` is feature-organized with 23 grandfathered cross-feature imports and no module public-contract boundary; feature names diverge from the backend bounded-context glossary, persona/personas are duplicated, and two `useBlogPosts()` hooks conflate carousel articles with first-class blog posts. The frontend needs the same bounded-context ownership + enforceable boundaries the backend now has.

## Scope

Behavior-preserving (App Router URLs + UI unchanged; green gates held; boundary ratchet down-only). Frontend-only. Work is scoped to this ticket's slice of the feature->module migration per `docs/plans/phase-7-frontend-alignment.md`; re-export shims keep `@/` paths resolving during the move.

## Non-Goals

- No backend RUNTIME/behavior change. (A read-only `app.openapi()` export script + committed artifact is the only backend-side addition — it does not alter any endpoint, schema, or response.)
- No App Router URL changes.
- No UI/behavior change; no test deletion or gate weakening.
- No exhaustive component re-homing or legacy-shim removal (deferred to Phase 8).

## Modularization Alignment (2026-06-16)

Phase 7 of the modularization plan (§Phase 7 "Align the frontend"). **Behavior-preserving** frontend
reorganization: App Router URLs unchanged, the green gates (typecheck + eslint + lint:boundaries + 822 Vitest
tests + check:legacy) stay green per ticket, and the feature/module-boundary ratchet only goes DOWN. Features
migrate into `frontend/src/modules/<context>` sharing the backend glossary (knowledge/identity/conversation/
editorial/carousel-presentation/publishing + editorial-operations/persona/quality), each behind a public contract;
re-export shims keep `@/` paths resolving during migration (object-identity, mirroring backend AE-0126).
ZERO gate-gaming (no new eslint-disable/@ts-ignore/@ts-expect-error/skipped tests/lowered thresholds/baseline
additions). Soft precondition: Phase 6 (PR #20) merging only finalizes glossary naming; this frontend-only work reads the committed glossary doc and does not hard-block on the backend merge. See `docs/plans/phase-7-frontend-alignment.md`.

## Acceptance Criteria

- [ ] A read-only export script SHALL dump FastAPI app.openapi() to a committed artifact (no app behavior change)
- [ ] A script SHALL compare the frontend Zod schemas to that OpenAPI artifact and report drift
- [ ] The check SHALL run in CI (advisory->blocking once green) and pass on the current code
- [ ] No runtime behavior change; existing backend + frontend gates green

## Gherkin Scenarios

Not applicable — behavior-preserving reorganization; verified by the green-gate safety net (typecheck + eslint
+ lint:boundaries + Vitest 822 + check:legacy) and the App Router URL inventory.

## Dependencies

- Blocks: AE-0142
- Blocked by: AE-0140
- Related: AE-0134

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-16

Ticket created by planner (Phase 7 breakdown).

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
