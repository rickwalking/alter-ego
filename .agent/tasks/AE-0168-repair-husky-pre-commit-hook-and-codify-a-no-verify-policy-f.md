# AE-0168 — Repair husky pre-commit hook and codify a --no-verify policy (format/lint defense-in-depth)

Status: Intake
Tier: T1
Priority: High
Type: Quality
Area: Cross-cutting
Owner: Unassigned
Branch: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Make the pre-commit hook reliable so prettier/lint-staged actually runs locally, and codify a `--no-verify` policy — eliminating the recurring "format gate fails late" class. Source: kaizen sweep `.agent/reports/kaizen-sweep-2026-06-16.plan.md` P3.

## Problem

The blocking `frontend:format` gate failed late in AE-0132, AE-0141, and AE-0154 because commits used `git commit --no-verify`, bypassing the husky pre-commit prettier/lint-staged step (the hook is locally unreliable). `--no-verify` also enabled a lost-commit incident (partial staging; see MEMORY). A flaky hook trains everyone to bypass it.

## Scope

- Repair `.husky/pre-commit` so `lint-staged` (prettier --write + eslint --fix on staged files) runs reliably; fix whatever makes it flaky (husky v9 / commitlint wiring).
- Codify a `--no-verify` policy (when acceptable) in `CLAUDE.md`/`AGENTS.md`.
- Defense-in-depth: keep the `frontend:format` CI gate blocking (already true) so a bypass is still caught in CI.

## Non-Goals

- Not demoting `frontend:format` to advisory or adding `prettier-ignore` (would loosen — rejected).
- Not removing `--no-verify` capability (needed for automation); make the hook reliable + document policy.

## Acceptance Criteria

- [ ] A normal `git commit` runs the hook; staged unformatted files are auto-fixed so they cannot land unformatted.
- [ ] Verified on a SEEDED unformatted staged file (commit fixes/blocks it).
- [ ] `--no-verify` policy documented in CLAUDE.md/AGENTS.md.
- [ ] `frontend:format` CI gate remains blocking (unchanged); no formatting drift on a fresh clone+commit.

## Repro Steps

1. On a recent `--no-verify` commit, run `npx prettier --check "src/**/*.{ts,tsx,json,css,md}"` → drift appears (e.g. AE-0154 left `use-editorial-analytics.ts` unformatted until a follow-up fix).
2. `bash scripts/ci/gates.sh frontend:format` → FAIL, even though typecheck/lint/test passed.

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
