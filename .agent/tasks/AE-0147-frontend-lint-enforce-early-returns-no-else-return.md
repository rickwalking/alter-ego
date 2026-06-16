# AE-0147 — Frontend lint: enforce early returns (no-else-return)

Status: Ready
Tier: T1
Priority: Medium
Type: Task
Area: Frontend/CI
Owner: Unassigned
Branch: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Enforce the "early returns over nested if" rule (a documented CLAUDE.md
convention) in the frontend lint gate.

## Problem

Source: kaizen incident on PR #21 (`.agent/reports/kaizen-pr21.plan.md`).
Reviewer flagged nested `if` at `knowledge/hooks/use-upload.ts:43`
("inner if statements, prefer early returns"). `max-depth=4` is too lax to catch
it and there is no `no-else-return` rule. The convention is documented but
unenforced.

## Scope

- Enable `no-else-return` (+ consider `sonarjs/prefer-immediate-return`) in
  `frontend/eslint.config.mjs`.
- Fix `use-upload.ts` to use guard clauses.
- (May be merged into AE-0145's PR.)

## Non-Goals

- Do not refactor unrelated code
- Lowering `max-depth`/`complexity` thresholds is a separate decision (and must
  only tighten, never loosen).

## Acceptance Criteria

- [ ] `no-else-return` enabled; `npm run lint:changed` fails on a seeded `else { return }`.
- [ ] `use-upload.ts` uses early returns; gate green.

## Repro Steps

1. Open `frontend/src/modules/knowledge/hooks/use-upload.ts:43` — nested if, no rule fires.

## Affected Areas

- [ ] Backend
- [ ] Frontend
- [ ] Tests

## Dependencies

None.

## Progress Log

### 2026-06-16 HH:mm

Ticket created.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
