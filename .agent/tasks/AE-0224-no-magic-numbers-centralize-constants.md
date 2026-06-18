# AE-0224 — no-magic-numbers + centralize API_BASE / HTTP_STATUS

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Frontend/CI
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0145-no-magic-numbers-centralize-constants
Kanban Card: AE-0224
Created: 2026-06-16
Updated: 2026-06-18

## Goal

PR #21 (Phase 7) review follow-up. no-magic-numbers + centralize API_BASE / HTTP_STATUS.

## Problem

PR #21 review: magic numbers (incl. HTTP status codes) and a scattered API base URL violate the no-magic-strings/numbers rule. HTTP_STATUS and API_BASE should be centralized constants.

## Scope

Centralize the API base URL (API_BASE) and HTTP status codes (HTTP_STATUS) into src/constants/ and replace scattered literals; enable eslint no-magic-numbers (with sensible ignores: 0/1/-1, array indices, test files) at a level that passes (or down-only baseline). Behavior-preserving (same URLs/status values).

## Non-Goals

- No behavior change beyond the stated fix.
- No App Router URL changes; existing green gates stay green.
- No gate-gaming (no eslint-disable/@ts-ignore/.skip/lowered thresholds/baseline additions beyond a documented down-only ratchet).

## Modularization Alignment (2026-06-16)

PR #21 (Phase 7 frontend alignment) review fix. Behavior-preserving; holds the Phase 7 green-gate safety net
(typecheck + eslint + lint:boundaries 0 + url:check 26 + lint:circular 0 + Vitest 822 + check:legacy + prettier
format) and the boundary ratchet (down-only). See `docs/plans/phase-7-frontend-alignment.md`.

## Acceptance Criteria

- [ ] API_BASE + HTTP_STATUS SHALL be centralized constants in src/constants/; scattered literals replaced
- [ ] eslint no-magic-numbers SHALL be enabled (idiomatic ignores) and pass (or down-only baseline; 0 new)
- [ ] Behavior-preserving (identical URLs/status values); typecheck + lint + Vitest 822 + build green

## Gherkin Scenarios

Not applicable — lint/CI/docs/dependency fix; verified by the green-gate safety net.

## Dependencies

- Blocks: —
- Blocked by: AE-0134
- Related: AE-0142

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-16

Ticket created from PR #21 review.

### 2026-06-18

Renumbered from **AE-0145** to resolve the duplicate-ID collision (AE-0181 dup
warning): AE-0145 is the *Done* same-work twin; this pending ticket kept its own card.
Demoted Review → Ready: the work was never developed under this twin (its
`Review` status had no dev/QA reports of its own). Still open frontend work.

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
