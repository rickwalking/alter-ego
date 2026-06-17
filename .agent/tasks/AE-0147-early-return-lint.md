# AE-0147 — Early-return / guard-clause lint rule

Status: Done
Tier: T1
Priority: High
Type: Task
Area: Frontend/CI
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0147-early-return-lint
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

PR #21 (Phase 7) review follow-up. Early-return / guard-clause lint rule.

## Problem

PR #21 review: the CLAUDE.md 'early returns preferred; avoid nested if' rule is not lint-enforced on the frontend. Deeply-nested conditionals can regress without a guard.

## Scope

Enable an ESLint rule enforcing early returns / limiting nesting depth (e.g. no-else-return + sonarjs/eslint max-depth or equivalent) at a level that passes the current code (or with a documented down-only baseline if pre-existing violations exist). No logic change.

## Non-Goals

- No behavior change beyond the stated fix.
- No App Router URL changes; existing green gates stay green.
- No gate-gaming (no eslint-disable/@ts-ignore/.skip/lowered thresholds/baseline additions beyond a documented down-only ratchet).

## Modularization Alignment (2026-06-16)

PR #21 (Phase 7 frontend alignment) review fix. Behavior-preserving; holds the Phase 7 green-gate safety net
(typecheck + eslint + lint:boundaries 0 + url:check 26 + lint:circular 0 + Vitest 822 + check:legacy + prettier
format) and the boundary ratchet (down-only). See `docs/plans/phase-7-frontend-alignment.md`.

## Acceptance Criteria

- [ ] An ESLint rule discouraging unnecessary else-after-return / excessive nesting SHALL be enabled
- [ ] The rule SHALL pass on current code (or grandfather pre-existing violations with a down-only baseline; 0 new)
- [ ] No behavior change; eslint + typecheck + Vitest 822 green

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

DONE — verified in main. Early-return lint enforced: `no-else-return` + `no-lonely-if` active in `frontend/eslint.config.mjs`. Landed in main; phase-7 branch superseded.
