# AE-0333 — deploy: pull and build before down so a registry failure is not an outage

Status: Ready
Tier: T1
Priority: Critical
Type: Bug
Area: Backend
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-09-15
Updated: 2026-09-15

## Goal

Make a failed `docker compose pull` or `build` a **no-op deploy** instead of a
production outage. Prod must never be taken down before the new images it needs
are proven to exist locally.

## Problem

`.github/workflows/deploy.yml` runs, in this order (lines 172-176):

```bash
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml build
```

On 2026-09-15 the merge of PR #87 hit `pull access denied for minio/minio`
(Docker Hub removed the image). `set -e` aborted the script **after `down` and
before `build`/`up`** — prod went from 10 containers to zero and
`marinssolutions.com` answered **521 for ~40 minutes**. Recovery was manual:
bring the app tier back on the still-local images
(`up -d --no-build --pull never postgres redis backend frontend nginx certbot`),
then the Langfuse tier, then rebuild and swap.

AE-0331 fixed *that* pull (pinned `quay.io/minio/minio`), but the ordering is the
actual defect: **any** future registry outage, rate limit, expired credential, or
upstream image deletion reproduces the same total outage. The registry is a third
party we do not control; the ordering is ours.

There is no rollback path either — once `down` has run, the script has no step
that restores the previous state on failure.

## Scope

- `.github/workflows/deploy.yml`: reorder to `pull` → `build` → (migrations) →
  `up -d` with `down` removed or replaced by compose's own recreate.
  `docker compose up -d` already stops/recreates only the containers whose spec
  or image changed, so the explicit `down` is not needed for correctness.
- Guard the pull/build step so a failure **exits before touching the running
  stack**, with a clear log line saying prod was left untouched.
- If an explicit `down` must stay for a specific service (e.g. to free a port),
  scope it to that service and run it *after* the images are present.
- Add a post-deploy health assertion that fails the workflow if the site is not
  200 afterwards (so a half-deploy is loud).

## Non-Goals

- Blue/green or zero-downtime deploys — this ticket only removes the
  *catastrophic* failure mode, not the ~12-minute recreate blip.
- Changing which images are pinned (AE-0331 did that).
- Re-enabling the Alembic migrate-on-deploy step (still disabled; two heads).

## Acceptance Criteria

- [ ] `deploy.yml` performs `pull` and `build` **before** any step that stops a
      running container.
- [ ] A simulated pull failure (an intentionally bogus image reference in a
      scratch compose file, or a dry-run against an unreachable registry) leaves
      the running stack **up** — verified by container count before/after.
- [ ] The workflow exits non-zero on such a failure with a message stating that
      prod was left running.
- [ ] A post-`up` health check asserts `https://marinssolutions.com/` returns 200
      and fails the job otherwise.
- [ ] The next real `main` deploy completes green.

## Gherkin Scenarios

```gherkin
Feature: Deploy ordering protects production

  Scenario: The registry is unavailable when a deploy starts
    Given production is running with 10 containers
    When the deploy runs and "docker compose pull" fails
    Then the deploy exits non-zero
    And production is still running with 10 containers
    And the log states that production was left untouched

  Scenario: A normal deploy still replaces the images
    Given a commit lands on main with a changed backend Dockerfile
    When the deploy runs
    Then the new image is built before any container is stopped
    And the stack comes up on the new image
    And the site returns 200
```

## Affected Areas

- Backend: no source change
- Frontend: no
- Database: no
- API: no
- Tests: workflow-level verification (simulated pull failure)
- Docs: `docs/deployment/` — record the ordering invariant
- Prompts/LLM: no
- Observability: deploy log messaging
- Deployment: yes — this is the whole ticket

## Dependencies

- Blocks: safe merges to `main` (every merge auto-deploys)
- Blocked by: none
- Related: AE-0331 (the quay pin), AE-0207 (the previous deploy-caused outage)

## Implementation Plan

1. Reorder the block in `deploy.yml`; delete the unconditional `down`.
2. Wrap pull/build in a step whose failure message is explicit; keep `set -e`.
3. Add the post-`up` curl health assertion.
4. Simulate a pull failure on a scratch compose file on the droplet and record
   container counts before/after as evidence.
5. Document the invariant ("never stop the stack before the images are local")
   in `docs/deployment/` and in root `CLAUDE.md`'s deploy warning.

## QA Checklist

- [ ] Security reviewed (no secret handling changed)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (build succeeds but up fails; partial image set)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-09-15

Ticket created. Deliberately split out of AE-0331, which fixed only the specific
image reference. Root cause confirmed at `.github/workflows/deploy.yml:172-176`.

## Files Touched

Pending.

## Test Evidence

Pending. CI/deployment-config ticket (AE-0153 no-`.feature` path is available,
but the Gherkin above is kept because the failure mode is observable behaviour).
Verification is the simulated pull failure with before/after container counts.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
