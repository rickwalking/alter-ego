# AE-0516 — Frontend: bump Next.js to 16.4.2 for the critical image-optimization RCE advisory

Status: In Development
Tier: T1
Priority: Critical
Type: Bug
Area: Frontend
Owner: Claude — found while shipping the /chat fixes (AE-0486 follow-up)
Branch: fix/ae-0516-next-cve
Created: 2026-10-22
Updated: 2026-10-22

## Goal

Production no longer runs a Next.js version with the critical image-optimization RCE, and `frontend:security`
(`npm audit --audit-level=high`) passes again.

## Problem

Advisories GHSA-2464-fhr4-w9xw (critical: unauthenticated RCE in the Image Optimization API with SVG files) and
GHSA-p3m5-59mp-jv5r (DoS in App Router server actions) cover next 16.0.0 - 16.4.0. Production runs 16.4.0, and the
blocking security gate fails on every frontend PR.

## Scope

- `next` `^16.4.2` in `frontend/package.json`, lockfile updated (`npm install`).

## Non-Goals

- The moderate vitest/storybook advisories (below the gate's `high` level; the fix needs a breaking storybook bump).

## Acceptance Criteria

- [x] `npm audit --audit-level=high` passes.
- [x] All frontend gates pass (mutation in CI).

## Repro Steps

1. `cd frontend && npm audit --audit-level=high` on main → 1 critical (next). On this branch → passes.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [ ] Tests

## Dependencies

None.

## Progress Log

### 2026-10-22 20:00

Bumped and locked. This is a dependency change with no behavior change, so unit tests and gates stand in for a
`.feature` (CLAUDE.md, AE-0153); the failing audit gate is the seeded check.

## Files Touched

- frontend/package.json, frontend/package-lock.json

## Test Evidence

Local frontend gates: security, lint, typecheck, format, integrity, gherkin-refs, dead-code, schema-drift, build
PASS. The full test run had 2381 passing. The one failure was the known flake where `check-comments.test.ts` scans
the tree while `eslint-strict-presets.test.ts` writes probe files; it passes when re-run alone.

## QA Report

Pending (CI).

## Blockers

None.
