# AE-0540 — Fix-forward: clear the filelock and langgraph-checkpoint-postgres advisories (backend pip-audit red on main)

Status: In Development
Tier: T1
Priority: High
Type: Chore
Area: Backend
Owner: Claude Code (claude-opus-5-5)
Branch: fix/ae-0540-backend-advisories
Created: 2026-10-23
Updated: 2026-10-23

## Goal

`main` is green again on `backend:pip-audit`.

## Problem

`bash scripts/ci/gates.sh backend:pip-audit` fails on `origin/main` (d383a979) with 4 advisories:
`filelock` 3.29.0 (fixed in 4.2.1) and `langgraph-checkpoint-postgres` 3.1.2 (fixed in 3.1.3).

## Scope

- `backend/pyproject.toml`: `langgraph-checkpoint-postgres>=3.1.3`; `filelock>=4.2.1` in
  `[tool.uv] override-dependencies` (it is transitive only, through `cachecontrol[filecache]` used by
  `pip-audit`).
- `backend/uv.lock` relocked with uv 0.13.5 (the CI pin), upgrading only these packages:
  `filelock` 3.29.0 -> 4.2.4, `langgraph-checkpoint-postgres` 3.1.2 -> 3.1.3 and its required
  `langgraph-checkpoint` 4.1.1 -> 4.3.0.

## Non-Goals

- Audit ignores, other dependency upgrades.

## Acceptance Criteria

- [x] `gates.sh backend:pip-audit` passes with no ignore list.
- [x] `filelock` 4 is safe here: no first-party import; its only consumer, `cachecontrol`'s `FileCache`
  (`from filelock import BaseFileLock, FileLock`), writes and reads a cache entry on 4.2.4.
- [x] The checkpointer-related tests and the backend unit suite pass on the new versions.

## No-`.feature` classification (dependency/CI ticket)

- (a) No public or user-visible behavior change: `filelock` is a major bump but only the dev tool `pip-audit`
  (through `cachecontrol`) loads it, with an API that 4.x keeps; `langgraph-checkpoint` is a minor bump and
  `langgraph-checkpoint-postgres` a patch with the same saver API and the same table migrations.
- (b) Seeded-violation test: not a new gate or rule; the existing pip-audit gate fails on `main` before this
  change (4 advisories) and passes after.
- (c) Affected gates: `backend:pip-audit` (fixed), `backend:test`.
- (d) Reviewer/QA sign-off on the no-`.feature` classification: `.agent/reports/AE-0540.qa.md`.

## Affected Areas

- Backend: `backend/pyproject.toml`, `backend/uv.lock`. Frontend, database, API: none.

## Dependencies

- Blocked by: none.
- Blocks: every PR while `main` is red on pip-audit.

## Progress Log

### 2026-10-23

pip-audit red on `main`. Bumped the two packages, relocked with uv 0.13.5; pip-audit green; every test
file that mentions checkpoints (69 files, 715 passed) and the backend unit suite green.

## Files Touched

- `backend/pyproject.toml`, `backend/uv.lock`.

## Test Evidence

`.agent/reports/AE-0540.dev-summary.md`.

## QA Report

`.agent/reports/AE-0540.qa.md`.

## Decision Log

- 2026-10-23 — Pin `langgraph-checkpoint-postgres` to the first fixed patch line (3.1.3) rather than 3.2.0
  to keep the upgrade minimal.

## Blockers

None.
