# AE-0345 — dev compose still points at the deleted Docker Hub MinIO images

Status: Ready
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-09-15
Updated: 2026-09-15

## Goal

A fresh `docker compose up` must work. Local development and onboarding must not
fail on an image that no longer exists.

## Problem

Found by external QA on the merged AE-0331 work (2026-09-15). AE-0331 moved the
**production** compose file to quay but left the **development** one pointing at
the very images Docker Hub removed:

```yaml
# docker-compose.yml:116
image: minio/minio:latest
# docker-compose.yml:136
image: minio/mc:latest
```

These are the same `minio/minio` references that produced
`pull access denied for minio/minio` and took prod down for 40 minutes. So every
developer who pulls, and every fresh clone that runs `docker compose up`, hits the
identical failure — the Langfuse tier simply cannot start locally.

Two problems, not one: the repository is gone, **and** `:latest` is unpinned, so
even a working `latest` would give different bytes to different developers.

The ticket's "any other image pin" non-goal reasonably excluded *unrelated*
images. It does not cover leaving the *same broken image* in the tree.

## Scope

- `docker-compose.yml`: point `minio` and the init service at
  `quay.io/minio/minio` at the **same pinned release** used in prod, so dev and
  prod run the same MinIO.
- Replace `minio/mc:latest`: prod's init service uses the `minio` image itself
  rather than `mc` — mirror that, or pin an equivalent client image that is
  actually pullable.
- Pin by tag at minimum; by digest if AE-0344 lands first (prefer matching
  whatever AE-0344 settles on).
- Sweep `docker-compose.yml` (and any other compose/override files) for other
  `:latest` or Docker-Hub-only references and report them.
- Verify a clean `docker compose up` from a fresh state on a machine with no
  cached images.

## Non-Goals

- Changing the local development topology.
- The production pin (AE-0331 did it; AE-0344 hardens it).
- The deploy ordering (AE-0333).

## Acceptance Criteria

- [ ] `docker-compose.yml` no longer references `minio/minio` or `minio/mc` on
      Docker Hub.
- [ ] `docker compose pull` succeeds from a state with **no cached images**.
- [ ] `docker compose up` brings the Langfuse tier up locally, including bucket
      creation by the init service.
- [ ] No `:latest` on the MinIO images; dev and prod run the same MinIO release.
- [ ] Any other unpinned or Docker-Hub-only reference found in the sweep is
      listed in the ticket.

## Gherkin Scenarios

```gherkin
Feature: Local development starts from a clean machine

  Scenario: A fresh clone can pull every image
    Given a machine with no cached images for this project
    When docker compose pull runs
    Then every image is pulled successfully

  Scenario: The Langfuse tier starts locally
    Given the images are pulled
    When docker compose up runs
    Then MinIO starts and the init service creates its buckets

  Scenario: Dev and prod agree on the MinIO release
    Given both compose files
    When their MinIO references are compared
    Then they name the same release
```

## Affected Areas

- Backend: no source change
- Frontend: no
- Database: no
- API: no
- Tests: clean-machine pull/up verification
- Docs: onboarding notes if the local setup steps change
- Prompts/LLM: no
- Observability: no
- Deployment: dev environment

## Dependencies

- Blocks: onboarding and local Langfuse work
- Blocked by: none (coordinate with AE-0344 on tag vs digest)
- Related: AE-0331, AE-0344

## Implementation Plan

1. Point both dev services at the quay reference used in prod.
2. Mirror prod's approach for the init/client service.
3. Verify with a pruned local image cache (`docker image rm` the MinIO images
   first, so the test is real).
4. Sweep for other `:latest` / Docker-Hub-only references; report.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (no cached images; offline behaviour)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-09-15

Created from the retroactive external QA of AE-0331 (see
`.agent/reports/AE-0331.qa.md`). Confirmed directly at
`docker-compose.yml:116,136`.

## Test Evidence

Pending. Tooling/config ticket (AE-0153 no-`.feature` path available): no
public/user-visible behaviour change in the application — this restores the local
environment. Verification is a clean-cache `docker compose pull` and `up`.

## Files Touched

Pending.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
