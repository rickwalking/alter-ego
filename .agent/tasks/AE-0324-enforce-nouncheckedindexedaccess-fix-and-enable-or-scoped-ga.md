# AE-0324 — enforce nouncheckedindexedaccess: fix-and-enable or scoped gate plus down-only baseline

Status: Dev Complete
Tier: T2
Priority: Medium
Type: Quality
Area: frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/kaizen-wave-ae0322-0328
Kanban Card: TBD
Created: 2026-07-22
Updated: 2026-07-22

## Goal

The "unguarded `Record[key]` lookup → prod TypeError" class becomes a
compile-time or gate-time error: `noUncheckedIndexedAccess` is enabled (fully or
via a scoped, down-only-ratcheted gate) — this ticket may NOT close on a
measurement report alone.

## Problem

Kaizen failure class FC-4 (`.agent/reports/kaizen-session-2026-07-22.signal.md`).
Prod incident (AE-0295): `badge.tsx` destructured
`BLOG_POST_BADGE_COLORS[color]` with no fallback; workflow statuses weren't keys
→ `TypeError` on every non-featured card → the entire admin blog listing
crashed. The instance was fixed (typed map + neutral fallback) but the CLASS is
unenforced: `noUncheckedIndexedAccess` is absent from every frontend tsconfig
(verified 2026-07-22), so the next unguarded indexed access ships silently.

## Scope

Pre-committed decision rule (cold-critic WARN-4 — no open-ended spike):

1. Run `tsc --noEmit` with `noUncheckedIndexedAccess: true`; count and classify
   errors.
2. **≤40 errors** → fix all fallout and enable the flag in
   `frontend/tsconfig.json` in THIS ticket.
3. **>40 errors** → THIS ticket still lands an enforceable artifact: a dedicated
   `tsconfig.strict-index.json` typecheck gate (flag ON) over an allowlisted
   directory set (at minimum the directories touched by AE-0295), plus a
   down-only error-count baseline for the remainder, wired into
   `gates.sh frontend`. Follow-up ticket for full adoption emitted at completion.

## Non-Goals

- No behavioural changes beyond adding the guards/fallbacks the flag demands.
- No blanket `!` non-null assertions to silence the flag (that is gaming; a
  net-new `!` on indexed access in the diff should be treated as suspect in
  review/QA).

## Acceptance Criteria

- [x] Fallout measured and the count recorded in the ticket (with the ≤40/>40
      branch taken stated explicitly).
- [x] An enforceable artifact is live: flag ON repo-wide, OR scoped gate +
      down-only baseline wired into `gates.sh frontend`.
- [x] AE-0180 rule-fires test: a seeded unguarded `Record[key]` access in an
      enforced path FAILS the typecheck/gate.
- [x] Existing tests and build green.

## Repro Steps

1. Write `const { bg } = SOME_RECORD[someString]` where `someString` may not be
   a key.
2. `npm run typecheck` → today: passes; at runtime → TypeError (the AE-0295 prod
   crash shape).

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None.

## Decision Log

- Cold-critic WARN-4 (2026-07-22): "measure-then-decide" spikes hide indefinite
  deferral. Resolved: decision threshold (40) fixed up front; both branches land
  an enforceable gate; closure on a report alone is disallowed by AC.

## Progress Log

### 2026-07-22 — development complete (wave feat/kaizen-wave-ae0322-0328)

Decision rule: 76 > 40 -> gate branch. Shipped tsconfig.strict-index.json (flag ON, whole tree) + check-strict-index.mjs against a DOWN-ONLY per-file baseline (new files zero-enforced everywhere -- strictly stronger than a dir allowlist; every AE-0295 file enforced), wired into npm run lint (frontend lint gate locally + CI). Follow-up full-adoption ticket AE-0329 emitted per AC. Commit ca849a36.

### 2026-07-22

Ticket created by kaizen session-2026-07-22 (proposal P4). Plan:
`.agent/reports/kaizen-session-2026-07-22.plan.md`.

## Files Touched

- frontend/tsconfig.strict-index.json
- frontend/scripts/check-strict-index.mjs
- frontend/scripts/generate-strict-index-baseline.mjs
- frontend/scripts/strict-index-baseline.json
- frontend/src/scripts/strict-index.test.ts
- frontend/package.json
- frontend/AGENTS.md

## Test Evidence

Measured fallout: 76 errors across 30 files (>40 -> scoped-gate branch). npx vitest run src/scripts/strict-index.test.ts -> 7 passed (seeded unguarded Record[key] destructure FAILS the real tsc-backed checker; guarded access passes; baselined file tolerated; comparator NEW/GREW/TOTAL rules). node scripts/check-strict-index.mjs -> OK at baseline 76. Generator refuses count increases (verified: REFUSED at seeded count 0).

## QA Report

Pending.

## Blockers

None.
