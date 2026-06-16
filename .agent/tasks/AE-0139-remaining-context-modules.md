# AE-0139 — carousel-presentation + persona + quality + conversation + knowledge modules (+ identity docs note)

Status: Review
Tier: T2
Priority: High
Type: Task
Area: Frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0139-remaining-context-modules
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Migrate the remaining features into their modules per the ACCEPTED glossary (persona and quality are TWO contexts; persona_quality is forbidden): carousel->carousel-presentation (preview/review/refinement); persona+personas->persona (consolidating the persona/personas duplication); rubrics->quality (owns quality rubrics; depends on persona ONLY via persona's public contract); chat->conversation; knowledge->knowledge - each behind a public contract. IDENTITY: there is no features/auth — auth/session lives in lib/ + app/; this ticket does NOT relocate it (route-adjacent, risky), it only adds a docs note that frontend identity consolidation is deferred to Phase 8.

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

- [ ] carousel->carousel-presentation, chat->conversation, knowledge->knowledge SHALL live under their module behind a public contract
- [ ] persona + personas SHALL be consolidated under the `persona` module (no duplicate); rubrics SHALL live under the separate `quality` module, depending on persona only via persona's public contract (NO persona_quality module — glossary-forbidden)
- [ ] identity SHALL be a docs-only note (auth/session stays in lib/+app/; consolidation deferred to Phase 8) — no code move
- [ ] App Router URLs + UI unchanged; re-export shims keep old paths resolving
- [ ] The boundary ratchet SHALL ratchet DOWN or hold; typecheck/eslint/test/build green

## Gherkin Scenarios

Not applicable — behavior-preserving reorganization; verified by the green-gate safety net (typecheck + eslint
+ lint:boundaries + Vitest 822 + check:legacy) and the App Router URL inventory.

## Dependencies

- Blocks: AE-0140, AE-0142
- Blocked by: AE-0136, AE-0138
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
