# AE-0253 — reconcile validate_skill_boundary with model-invocable delivery skills

Status: Dev Complete
Tier: T1
Priority: High
Type: Quality
Area: Cross-cutting
Owner: Unassigned
Branch: TBD
Created: 2026-06-19
Updated: 2026-06-19

## Goal

Stop `validate_skill_boundary.py` from failing the backend `Test & Coverage` gate by
removing the obsolete `disable-model-invocation: true` requirement on delivery skills
(they are intentionally model-invocable now).

## Problem

`backend/tests/unit/scripts/test_validate_skill_boundary.py::test_skill_boundary_validation_passes`
fails on the whole branch stack (PRs #54/#56/#57): the validator still demands
`disable-model-invocation: true` in every delivery skill's frontmatter, but commit
`04a883b6` ("allow model invocation of delivery skills") deliberately removed that field
so the orchestrator can invoke `developer-skill` / `qa-agent` / etc. via the Skill tool
(the `skill-slash-command-registration` policy this delivery workflow depends on). The
validator was never updated, so it reports `Missing disable-model-invocation: true` for
all 7 delivery skills → `pytest` exits 1 → `Test & Coverage` → `backend-gate` → `ci-gate`
all FAIL. This is the single blocking failure across the stack (2273 other tests pass).

## Scope

- `scripts/validate_skill_boundary.py` — remove the `disable-model-invocation` check +
  the now-unused `DISABLE_PATTERN`; keep every other structural check.
- `backend/tests/unit/scripts/test_validate_skill_boundary.py` — fix the stale docstring;
  add a seeded-violation test (name != folder still fires) so the validator stays proven.

## Non-Goals

- Do not restore `disable-model-invocation: true` (would break Skill-tool invocation).
- Do not weaken the other structural checks (name==folder, no dup names, required slash
  commands, runtime/delivery separation, Dockerfile copies only runtime skills).

## Acceptance Criteria

- [x] `validate_skill_boundary.py` no longer requires `disable-model-invocation` on
      delivery skills; the validator runs clean on the real tree.
- [x] `test_skill_boundary_validation_passes` passes; a seeded `name != folder` test
      proves the validator still fires on a violation, and a control passes.
- [x] Full backend `pytest` is green (0 failures); `backend:lint`/`type`/`integrity` green.

## Repro Steps

1. `cd backend && uv run pytest tests/unit/scripts/test_validate_skill_boundary.py` →
   was 1 failed; now 3 passed.
2. `uv run python scripts/validate_skill_boundary.py` → `Skill boundary validation passed`.

## Affected Areas

- [x] Backend (scripts/ tooling + its unit test)
- [ ] Frontend
- [x] Tests

## Dependencies

None. Unblocks the `Test & Coverage` gate on PRs #54/#56/#57 (the stack landing).

## Test Classification (CLAUDE.md AE-0153 / AE-0180)

- **CI/tooling ticket** — corrects an obsolete static-analysis check. No `.feature`
  required; the seeded `name != folder` test keeps the rule proven (it is a check
  *removal*, not a new rule, so AE-0180's add-a-rule mandate does not apply).
- No public/user-visible behavior change.

## Progress Log

### 2026-06-19

Created + implemented (CI hotfix to unblock the stack merge). Removed the obsolete
`disable-model-invocation` requirement; added seeded + control tests.

## Files Touched

- `scripts/validate_skill_boundary.py` — removed `DISABLE_PATTERN` + the check (comment
  documents the model-invocable policy).
- `backend/tests/unit/scripts/test_validate_skill_boundary.py` — docstring + seeded /
  control tests.

## Test Evidence

```
$ cd backend && uv run pytest tests/unit/scripts/test_validate_skill_boundary.py -q   # 3 passed
$ uv run python scripts/validate_skill_boundary.py                                     # passed
$ uv run pytest --cov=rag_backend -q   # 2276 passed (was 1 failed, 2273 passed)
```

## QA Report

Pending.

## Blockers

None.
