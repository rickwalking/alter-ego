# AE-0135 — Documented frontend baseline + context-mapping doc

Status: Review
Tier: T2
Priority: High
Type: Task
Area: Frontend/Docs
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0135-frontend-baseline-context-map
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Establish a documented frontend baseline (file/LOC measurement methodology + the green-gate snapshot) closing the round-2 'baseline does not reproduce' finding, plus a feature->module context-mapping doc, BEFORE any code moves.

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

- [ ] A baseline doc SHALL record the measurement methodology (non-test file + LOC counts per feature) and the current green-gate snapshot (typecheck/eslint/lint:boundaries 23/test 822)
- [ ] A context-mapping doc SHALL map each current feature to its target module (per the plan table)
- [ ] No source code SHALL change (docs-only); all gates stay green

## Gherkin Scenarios

Not applicable — behavior-preserving reorganization; verified by the green-gate safety net (typecheck + eslint
+ lint:boundaries + Vitest 822 + check:legacy) and the App Router URL inventory.

## Dependencies

- Blocks: AE-0136
- Blocked by: —
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
