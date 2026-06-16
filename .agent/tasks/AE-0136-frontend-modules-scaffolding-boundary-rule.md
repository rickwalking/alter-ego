# AE-0136 — modules/ scaffolding + public-contract convention + module-boundary lint rule

Status: Review
Tier: T2
Priority: High
Type: Task
Area: Frontend/CI
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0136-frontend-modules-scaffolding-boundary-rule
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Introduce frontend/src/modules/<context>/ with a public-contract (barrel) convention and REFACTOR the existing feature-boundary checker to enforce module public contracts. Today scripts/feature-boundary.config.mjs hardcodes src/features + @/features/ and feature-boundary-scan.mjs derives the owner via split('/')[2] and only walks src/features — so modules/ + @/modules/* imports are invisible, and the app/ layer (which imports features 175+ times) is unmonitored. Parameterize the root dir / import prefix / owner-segment to cover BOTH features/ and modules/ during migration AND treat app/ as a consumer limited to module public contracts. Also add a new App-Router URL-inventory script (enumerate page.tsx/route.ts + their segment exports for pre/post diffing) and wire `npm run build` + a circular-import check (madge) as per-migration gates. No feature is moved yet (scaffolding + tooling only).

## Problem

Today `frontend/src/features/**` is feature-organized with 23 grandfathered cross-feature imports and no module public-contract boundary; feature names diverge from the backend bounded-context glossary, persona/personas are duplicated, and two `useBlogPosts()` hooks conflate carousel articles with first-class blog posts. The frontend needs the same bounded-context ownership + enforceable boundaries the backend now has.

## Scope

Behavior-preserving (App Router URLs + UI unchanged; green gates held; boundary ratchet down-only). Frontend-only. Work is scoped to this ticket's slice of the feature->module migration per `docs/plans/phase-7-frontend-alignment.md`; re-export shims keep `@/` paths resolving during the move.

## Non-Goals

- No backend changes (frontend-only).
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

- [ ] A documented modules/<context>/index.ts public-contract convention SHALL exist (the only cross-module import surface)
- [ ] The boundary checker SHALL be parameterized to scan BOTH src/features and src/modules, treat src/app as a consumer limited to module public contracts, and keep the ratchet (ceiling unchanged or lower; 0 new)
- [ ] A demonstrated+reverted violation SHALL prove the rule fails on an internal cross-module import (a @/modules/<m>/<internal> import from another module/app)
- [ ] A URL-inventory script SHALL enumerate App-Router page.tsx/route.ts + segment exports for pre/post diffing, and `npm run build` + a circular-import (madge) check SHALL be runnable as gates
- [ ] typecheck + eslint + test + build stay green

## Gherkin Scenarios

Not applicable — behavior-preserving reorganization; verified by the green-gate safety net (typecheck + eslint
+ lint:boundaries + Vitest 822 + check:legacy) and the App Router URL inventory.

## Dependencies

- Blocks: AE-0137, AE-0138, AE-0139
- Blocked by: AE-0135
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
