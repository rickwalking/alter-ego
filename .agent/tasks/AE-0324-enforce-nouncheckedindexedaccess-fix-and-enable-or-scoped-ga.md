# AE-0324 — enforce nouncheckedindexedaccess: fix-and-enable or scoped gate plus down-only baseline

Status: In Development
Tier: T2
Priority: Medium
Type: Quality
Area: frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
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

- [ ] Fallout measured and the count recorded in the ticket (with the ≤40/>40
      branch taken stated explicitly).
- [ ] An enforceable artifact is live: flag ON repo-wide, OR scoped gate +
      down-only baseline wired into `gates.sh frontend`.
- [ ] AE-0180 rule-fires test: a seeded unguarded `Record[key]` access in an
      enforced path FAILS the typecheck/gate.
- [ ] Existing tests and build green.

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

### 2026-07-22

Ticket created by kaizen session-2026-07-22 (proposal P4). Plan:
`.agent/reports/kaizen-session-2026-07-22.plan.md`.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
