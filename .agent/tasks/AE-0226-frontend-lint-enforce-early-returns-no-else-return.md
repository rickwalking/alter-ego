# AE-0226 — Frontend lint: enforce early returns (no-else-return)

Status: Dev Complete
Tier: T1
Priority: Medium
Type: Task
Area: Frontend/CI
Owner: Agent
Branch: feat/dev-wave-ae0220-0227
Kanban Card: AE-0226
Created: 2026-06-16
Updated: 2026-06-18

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
- (May be merged into the AE-0224 no-magic-numbers PR.)

## Non-Goals

- Do not refactor unrelated code
- Lowering `max-depth`/`complexity` thresholds is a separate decision (and must
  only tighten, never loosen).

## Acceptance Criteria

- [x] `no-else-return` enabled (error, `allowElseIf:false`) + `no-lonely-if` (AE-0147); rule-fires test `src/scripts/eslint-no-else-return-rule.test.ts` proves it ERRORS (severity 2) on a seeded `else { return }`.
- [x] `use-upload.ts` uses early returns; gate green (0 no-else-return/no-lonely-if findings).

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

### 2026-06-18

Renumbered from **AE-0147** to resolve the duplicate-ID collision (AE-0181 dup
warning): AE-0147 is the *Done* same-work twin; this pending (Ready) ticket kept
its own card. No content change — still open frontend lint work.

### 2026-06-18 — implemented

The rule (`no-else-return` + `no-lonely-if` as error) and the `use-upload.ts`
guard-clause fix were already shipped by the Done twin AE-0147 (0 findings today).
The genuine gap was the **AE-0180 rule-fires test**, now added. No production-code
change (would be redundant). Status held at In Development pending the wave gate.

## Files Touched

- `src/scripts/eslint-no-else-return-rule.test.ts` — new rule-fires regression test.

## Test Evidence

```
$ npx vitest run src/scripts/eslint-no-else-return-rule.test.ts        → 1 passed
$ npx eslint src/modules/knowledge/hooks/use-upload.ts (no-else-return) → 0 findings
```

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
