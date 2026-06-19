# AE-0227 — Fix the failing npm-audit high vuln (frontend Security gate)

Status: Done
Tier: T1
Priority: High
Type: Task
Area: Frontend/CI
Owner: Agent
Agent Lane: planner → architect → developer → qa → release
Branch: feat/dev-wave-ae0220-0227
Kanban Card: AE-0227
Created: 2026-06-16
Updated: 2026-06-18

## Goal

PR #21 (Phase 7) review follow-up. Fix the failing npm-audit high vuln (frontend Security gate).

## Problem

The 'frontend / Security' CI gate (npm audit --audit-level=high) FAILS on PR #21: 1 HIGH vuln in vite 7.0.0-7.3.3 (launch-editor NTLMv2 hash disclosure + vite server.fs.deny bypass on Windows). A non-breaking fix is available (npm audit fix bumps vite within range).

## Scope

Resolve the HIGH-severity advisory so npm audit --audit-level=high exits 0. Prefer the minimal non-breaking bump (npm audit fix); avoid major/breaking upgrades. Commit the updated package-lock.json. Confirm typecheck/lint/test/build still green (vite backs vitest/storybook).

## Non-Goals

- No behavior change beyond the stated fix.
- No App Router URL changes; existing green gates stay green.
- No gate-gaming (no eslint-disable/@ts-ignore/.skip/lowered thresholds/baseline additions beyond a documented down-only ratchet).

## Modularization Alignment (2026-06-16)

PR #21 (Phase 7 frontend alignment) review fix. Behavior-preserving; holds the Phase 7 green-gate safety net
(typecheck + eslint + lint:boundaries 0 + url:check 26 + lint:circular 0 + Vitest 822 + check:legacy + prettier
format) and the boundary ratchet (down-only). See `docs/plans/phase-7-frontend-alignment.md`.

## Acceptance Criteria

- [x] npm audit --audit-level=high SHALL exit 0 (no HIGH/CRITICAL) — **verified: exit 0, 0 high / 0 critical (7 moderate only).**
- [x] The fix SHALL be minimal/non-breaking — **N/A: no code change needed; the vite HIGH advisory was already resolved (superseded by the Done twin AE-0148).**
- [x] package-lock.json updated; gates stay green — **N/A: no dependency change in this ticket; lockfile untouched.**

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

Renumbered from **AE-0148** to resolve the duplicate-ID collision (AE-0181 dup
warning): AE-0148 is the *Done* same-work twin; this pending ticket kept its own card.
Demoted Review → Ready (no dev/QA reports under this twin). Re-verify the
npm-audit HIGH advisory is still open before working — the Done twin may have
already resolved it.

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

No code change required. On re-verification (2026-06-18) the frontend Security
gate (`npm audit --audit-level=high`) **exits 0** — 0 high / 0 critical (only 7
moderate `next`-transitive advisories via storybook/vercel-analytics, which the
gate does not block). The original vite HIGH advisory that AE-0148 targeted is
already resolved in the current lockfile. This ticket is the renumbered pending
twin of the Done AE-0148; the work it described is complete, so it is closed Done
with evidence rather than fabricating a redundant fix.

Evidence:
```
$ npm audit --audit-level=high; echo $?        → 0
vulnerabilities: {high: 0, critical: 0, moderate: 7}
```
