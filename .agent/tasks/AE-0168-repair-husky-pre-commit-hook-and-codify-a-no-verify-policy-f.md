# AE-0168 — Repair husky pre-commit hook and codify a --no-verify policy (format/lint defense-in-depth)

Status: Dev Complete
Tier: T1
Class: B
Priority: High
Type: Quality
Area: Cross-cutting
Owner: developer-skill
Branch: chore/phase-8-class-b
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

- [x] A normal `git commit` runs the hook; staged unformatted files are auto-fixed so they cannot land unformatted. **Root causes fixed:** (1) hooks ran from the repo root but lint-staged/eslint/prettier live in `frontend/node_modules` → hooks now `cd frontend`; (2) git's `GIT_DIR`/`GIT_WORK_TREE` env broke lint-staged's repo resolution inside a worktree → hooks `unset` them; (3) `commitlint` couldn't resolve `@commitlint/config-conventional` from the root `.commitlintrc.json` → config moved to `frontend/.commitlintrc.json`; (4) `core.hooksPath` was an absolute path → `frontend` `prepare` now sets a relative `.husky` (worktree-safe).
- [x] Verified on a SEEDED unformatted staged file: `git commit` (no `--no-verify`) formatted `{a:1,b:2}` → `{ a: 1, b: 2 }` and committed; a non-conventional message was REJECTED by commitlint. See `frontend/tests/features/husky-precommit.feature`.
- [x] `--no-verify` policy documented in `CLAUDE.md` (Git & Commits) + `frontend/AGENTS.md`.
- [x] `frontend:format` CI gate unchanged (still blocking) — defense-in-depth.

## Files Touched

- `.husky/pre-commit`, `.husky/commit-msg` — cd frontend, unset git worktree env, run local tools.
- `frontend/.commitlintrc.json` — moved from repo root (preset resolves from frontend/node_modules).
- `frontend/package.json` — `prepare` sets relative `core.hooksPath` (guarded for Docker/no-git).
- `CLAUDE.md`, `frontend/AGENTS.md` — `--no-verify` policy.
- `frontend/tests/features/husky-precommit.feature` — Gherkin verification.

## Test Evidence

Seeded unformatted `frontend/src/_husky_probe.ts` (`export const HUSKY_PROBE   =    {a:1,b:2};`)
→ `git commit -m "test(ae-0168): ..."` (no `--no-verify`) → committed as
`export const HUSKY_PROBE = { a: 1, b: 2 };` (prettier-formatted). Bad message
`"not a conventional message"` → commitlint: `subject may not be empty`,
`type may not be empty` → commit blocked. Probe removed after verification.

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
