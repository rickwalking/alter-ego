# AE-0148 — Fix the failing npm-audit high vuln (frontend Security gate)

Status: Review
Tier: T1
Priority: High
Type: Task
Area: Frontend/CI
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0148-fix-npm-audit-high-vuln
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

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

- [ ] npm audit --audit-level=high SHALL exit 0 (no HIGH/CRITICAL)
- [ ] The fix SHALL be minimal/non-breaking (no major dependency upgrade unless unavoidable + justified)
- [ ] package-lock.json updated; typecheck + lint + Vitest 822 + build stay green

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

Pending.
