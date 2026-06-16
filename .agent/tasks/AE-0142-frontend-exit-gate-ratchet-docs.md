# AE-0142 — Frontend module-boundary exit gate + ratchet down + docs

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Frontend/CI
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0142-frontend-exit-gate-ratchet-docs
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Finalize the Phase 7 exit gate: ratchet the feature/module-boundary baseline DOWN to the post-migration count, enforce the module public-contract rule, document the frontend module conventions + the shared glossary, and record the deferred items (exhaustive component re-homing, route-page thinning, legacy shim removal) as a Phase 8 follow-up.

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
editorial/presentation/publishing + editorial-operations/persona-quality), each behind a public contract;
re-export shims keep `@/` paths resolving during migration (object-identity, mirroring backend AE-0126).
ZERO gate-gaming (no new eslint-disable/@ts-ignore/@ts-expect-error/skipped tests/lowered thresholds/baseline
additions). Precondition: Phase 6 (PR #20) merged. See `docs/plans/phase-7-frontend-alignment.md`.

## Acceptance Criteria

- [ ] The boundary baseline SHALL be ratcheted DOWN to the post-migration cross-context count (or held) and stay 0-new
- [ ] The module public-contract rule SHALL be enforced (demonstrated+reverted violation)
- [ ] Frontend module conventions + the shared backend/frontend glossary SHALL be documented
- [ ] The deferred items SHALL be recorded as a consent-gated Phase 8 follow-up
- [ ] typecheck + eslint + lint:boundaries + test + check:legacy green

## Gherkin Scenarios

Not applicable — behavior-preserving reorganization; verified by the green-gate safety net (typecheck + eslint
+ lint:boundaries + Vitest 822 + check:legacy) and the App Router URL inventory.

## Dependencies

- Blocks: AE-0134
- Blocked by: AE-0137, AE-0138, AE-0139, AE-0140, AE-0141
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
