# AE-0224 — no-magic-numbers + centralize API_BASE / HTTP_STATUS

Status: In Development
Tier: T2
Priority: High
Type: Task
Area: Frontend/CI
Owner: Agent
Agent Lane: planner → architect → developer → qa → release
Branch: feat/dev-wave-ae0220-0227
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

- [x] API_BASE + HTTP_STATUS SHALL be centralized constants in src/constants/; scattered literals replaced — **done: `src/constants/api.ts` exports `API_BASE = "/api"` and `HTTP_STATUS`; 0 no-magic-numbers findings in src/modules.**
- [x] eslint no-magic-numbers SHALL be enabled (idiomatic ignores) and pass — **done: `error` with ignores [-1,0,1,2,100] + arrayIndexes/defaults/enums; gate green.**
- [x] **Rule-fires test (AE-0180):** `src/scripts/eslint-no-magic-numbers-rule.test.ts` proves the rule ERRORS (severity 2) on a seeded magic number.
- [x] Behavior-preserving (identical URLs/status values).

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

### 2026-06-18 — implemented

Verified the substantive centralization + rule are already in place (shipped by the
Done twin AE-0145): `API_BASE`/`HTTP_STATUS` in `src/constants/api.ts`,
`no-magic-numbers: error` in `eslint.config.mjs`, 0 findings in src/modules. The
genuine gap was the **AE-0180 rule-fires test**, now added. No production-code
change (would be redundant/fabricated). Status held at In Development pending the
wave gate run.

## Files Touched

- `src/scripts/eslint-no-magic-numbers-rule.test.ts` — new rule-fires regression test.

## Test Evidence

```
$ npx vitest run src/scripts/eslint-no-magic-numbers-rule.test.ts   → 1 passed
$ grep -n "API_BASE\|HTTP_STATUS =" src/constants/api.ts            → API_BASE="/api", HTTP_STATUS={...}
$ npx eslint --format json "src/modules/**/*.ts" | (count no-magic-numbers) → 0
```

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
