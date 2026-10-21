# AE-0448 — Mutation runs in CI only

Status: In Development
Tier: T1
Priority: Medium
Type: Chore
Area: Cross-cutting
Owner: Claude (worker)
Branch: rickwalking/ae-0446-ci-only-mutation
Created: 2026-10-21
Updated: 2026-10-21

## Goal

Local mutation runs are impossible by default; agents and people take the
mutation verdict from the CI jobs on the PR head instead (AE-0446 follow-up).

## Problem

Local mutmut / Stryker runs run the dev machine out of memory (OOM), and the
repo's own skills told agents to run them ("mutation is slow but REQUIRED ... do
not skip"). Pedro decided mutation runs in CI only.

## Scope

- `scripts/lib/mutation_ci_only.sh`: guard that returns SKIP (77) with a one-line
  CI-only message outside GitHub Actions; `ALLOW_LOCAL_MUTATION=1` opts back in.
- Guard every local entry point: `gates.sh` `backend:mutation` /
  `frontend:mutation`, `scripts/ci/mutation-score-gate.sh`, `npm run test:mutate`.
- Skills (qa-agent, developer-skill, kaizen-skill), root/backend/frontend
  `CLAUDE.md`, and `docs/guides/qa-checkpoints.md`: never run mutation locally;
  read it from the CI job (`gh pr checks` / `gh run view --log`). The qa-agent
  verdict still requires the CI mutation job to be green.

## Non-Goals

- Do not refactor unrelated code
- No threshold, ratchet or baseline change; no CI workflow change. In CI
  (`GITHUB_ACTIONS=true`) the guard is bypassed, thresholds stay (backend
  blocking ≥75%, frontend Stryker break 30), and `GATES_REQUIRE_ALL=1` still
  turns any SKIP into a FAIL.

## Acceptance Criteria

- [x] Outside CI, `gates.sh backend:mutation` and `frontend:mutation` report SKIP
      (gate exit 77) with the CI-only message without starting mutmut / Stryker.
- [x] `mutation-score-gate.sh` and `npm run test:mutate` called directly exit 77
      locally without starting mutmut / Stryker.
- [x] `GITHUB_ACTIONS=true` (or `ALLOW_LOCAL_MUTATION=1`) does not skip.
- [x] Skills and CLAUDE.md tell agents to read mutation from CI, never run it.
- [ ] CI green on the PR, both mutation jobs included.

## Classification (no `.feature`, AE-0153 CI/tooling path)

- (a) **No public / user-visible behaviour change** — CI/tooling only; the app,
  API and CI verdicts are unchanged.
- (b) **Seeded-violation test** —
  `backend/tests/unit/scripts_ci/test_mutation_ci_only.py`: `uv` / `npm` are
  replaced by recording stubs; removing the guard from `frontend:mutation` or
  `mutation-score-gate.sh` makes the local-skip tests fail (checked by hand).
- (c) **Affected gates** — `backend:mutation`, `frontend:mutation` (local
  behaviour only); `backend:test` runs the new tests.
- (d) **QA sign-off** — pending (qa-agent report).

## Repro Steps

1. `bash scripts/ci/gates.sh backend:mutation` on a dev machine.
2. Before: mutmut starts and the machine runs out of memory.
3. After: one-line CI-only message, gate SKIP, nothing started.

## Affected Areas

- [x] Backend (tests only)
- [x] Frontend (`package.json` script)
- [x] Tests

## Dependencies

None. Related: AE-0446.

## Progress Log

### 2026-10-21 15:20

Ticket created. Guard, entry-point wiring, tests and docs implemented.

## Files Touched

- `scripts/lib/mutation_ci_only.sh` (new)
- `scripts/ci/gates.sh`, `scripts/ci/mutation-score-gate.sh`
- `frontend/package.json`
- `backend/tests/unit/scripts_ci/test_mutation_ci_only.py` (new)
- `CLAUDE.md`, `backend/CLAUDE.md`, `frontend/CLAUDE.md`,
  `docs/guides/qa-checkpoints.md`
- `skills/delivery/qa-agent/{SKILL.md,config.yaml,references/external-qa.md}`,
  `skills/delivery/developer-skill/{SKILL.md,references/wave-loop.md}`,
  `skills/delivery/kaizen-skill/SKILL.md`

## Test Evidence

- `uv run pytest tests/unit/scripts_ci/test_mutation_ci_only.py` — 8 passed
  (also with `GITHUB_ACTIONS=true GATES_REQUIRE_ALL=1` in the parent env).
- Mutation: CI only (this ticket); no local mutation run.

## QA Report

Pending.

## Blockers

None.
