# AE-0633 — Deploy workflow rejected: SSH script over GitHub's 21000-character expression cap

Status: In Development
Tier: T1
Priority: Critical
Type: Bug
Area: CI/CD
Owner: Pedro
Agent Lane: developer → qa → release
Branch: fix/ae-0633-deploy-script-length
Kanban Card: TBD
Created: 2026-11-20
Updated: 2026-11-20

## Goal

Make `deploy.yml` valid again so the AE-0631/AE-0632 merge (d6a8c2a22) deploys.

## Problem

The SSH step's `script` reads `${{ secrets.* }}`, so GitHub evaluates the whole script as one expression, capped at
21000 characters. AE-0631 grew it from 20905 to 21697 characters. GitHub refused the workflow file ("This run likely
failed because of a workflow file issue"): no job ran and nothing deployed. Prod stayed on 824c5686d, healthy, with
the reel cover columns already added by hand.

## Scope

- Move three historical note blocks (AE-0207 migrations, the disabled migrate-on-deploy note, the AE-0423 blog
  cutover) out of the script into YAML comments above the step. No command changes. The script is 19478 characters.
- `test_deploy_script_length_ae0633.py`: fails when the script reaches 21000 characters, with a seeded oversized
  check.

## Non-Goals

- Moving deploy steps into a `scripts/deploy/*.sh` file. That is the durable fix for headroom; follow-up.

## Acceptance Criteria

- [x] AC1 The SSH script is under 21000 characters (19478) with the same commands.
- [x] AC2 A test fails if the script reaches the cap; its seeded-violation check fires.
- [x] AC3 Every existing deploy-order test still passes.
- [ ] AC4 The deploy runs on main and its drift check passes.

## No-`.feature` classification (CI/config ticket)

- (a) No public or user-visible behaviour change: comments moved, no command changed.
- (b) Seeded-violation test: `test_the_cap_check_fires_on_an_oversized_script`.
- (c) Affected gates: `backend:test`; the deploy workflow itself.
- (d) Reviewer/QA sign-off on this classification: in the PR review.

## Files Touched

- `.github/workflows/deploy.yml`
- `backend/tests/unit/scripts_ci/test_deploy_script_length_ae0633.py`

## Test Evidence

- `uv run pytest tests/unit/scripts_ci`: 269 passed, 1 failed. The failure is
  `test_meta_ads_env_ae0579.py::test_service_gets_each_meta_ads_variable_with_an_empty_default[backend]`, an
  unraisable ResourceWarning leaked by an earlier test. It fails the same way on the main checkout without this
  change and passes on its own.
