# AE-0344 — re-pin MinIO by quay digest instead of a mutable tag

Status: Ready
Tier: T1
Priority: Medium
Type: Bug
Area: Backend
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-09-15
Updated: 2026-09-15

## Goal

Restore immutable image pinning for MinIO. What prod runs must not be able to
change without a commit.

## Problem

Found by external QA on the merged AE-0331 work (2026-09-15). Before the
incident, MinIO was pinned by **digest** — `minio/minio@sha256:14cea…` — which is
immutable: the bytes prod runs are fixed by the reference itself.

AE-0331 replaced it with a **tag**:

```yaml
# docker-compose.prod.yml:189 and :208
image: quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z
```

A tag is mutable. If quay repushes that tag, prod silently runs different bytes
on the next `compose pull`, with nothing in the repo changed to show it. That is
a supply-chain regression against the posture we had before.

Using a tag was the correct call *during* the incident — the registry was the
thing being worked around and the quay digest was unknown under time pressure —
but it should not be the resting state. The tag resolves now, so the digest is
available.

## Scope

- Resolve the digest for `quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z`
  (`docker manifest inspect` / `docker buildx imagetools inspect`) and pin both
  the `minio` and `minio-init` services to
  `quay.io/minio/minio@sha256:<digest>`.
- Keep the human-readable release in a comment next to each pin, so the version
  stays legible.
- Verify the digest is a multi-arch manifest list (or the right arch for the
  droplet) before pinning.
- Audit the other prod images for the same mutable-tag exposure and record what
  is found — pin them in this ticket only if trivial, otherwise list them.

## Non-Goals

- Upgrading the MinIO release (pin what is running).
- Adding automated digest-bump tooling (worth a follow-up, not this).
- The dev compose references (AE-0345).

## Acceptance Criteria

- [ ] `docker-compose.prod.yml` pins both MinIO services by `@sha256:` digest.
- [ ] `docker compose -f docker-compose.prod.yml pull --dry-run minio` succeeds
      against the digest on the droplet.
- [ ] The digest resolves to the same release currently running
      (`RELEASE.2025-09-07T16-13-09Z`), verified before and after.
- [ ] A comment records the human-readable release next to each pin.
- [ ] The deploy after the change completes green and MinIO comes up healthy.
- [ ] Any other prod image still on a mutable tag is listed in the ticket.

## Gherkin Scenarios

```gherkin
Feature: Production images are immutably pinned

  Scenario: MinIO is pinned by digest
    Given the production compose file
    When its image references are read
    Then both MinIO services are pinned by sha256 digest

  Scenario: The pinned digest is pullable
    Given the digest pin
    When a dry-run pull is performed on the droplet
    Then the pull succeeds

  Scenario: The digest matches the running release
    Given the digest pin
    When the image labels are inspected
    Then they report RELEASE.2025-09-07T16-13-09Z
```

## Affected Areas

- Backend: no source change
- Frontend: no
- Database: no
- API: no
- Tests: deploy verification
- Docs: deployment notes on the pinning policy
- Prompts/LLM: no
- Observability: no
- Deployment: yes

## Dependencies

- Blocks: immutable prod provenance
- Blocked by: none
- Related: AE-0331 (introduced the tag pin), AE-0345, AE-0333

## Implementation Plan

1. Resolve and record the digest; confirm the arch/manifest-list shape.
2. Pin both services; add the release comment.
3. Dry-run pull on the droplet.
4. Deploy and confirm MinIO healthy.
5. Sweep the remaining prod images for mutable tags and list them.

## QA Checklist

- [ ] Security reviewed (supply-chain posture restored)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (digest unavailable for the droplet's arch)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-09-15

Created from the retroactive external QA of AE-0331 (see
`.agent/reports/AE-0331.qa.md`). Confirmed directly against
`docker-compose.prod.yml:189,208`.

## Files Touched

Pending.

## Test Evidence

Pending. Deployment-config ticket (AE-0153 no-`.feature` path available): no
public/user-visible behaviour change — the same image bytes, referenced
immutably. Verification is the dry-run pull, the label check, and a green deploy.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
