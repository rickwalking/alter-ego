# AE-0331 — pin minio to quay.io so prod deploys stop failing at compose pull

Status: In Development
Tier: T1
Priority: Critical
Type: Bug
Area: Backend
Owner: Claude
Branch: fix/ae-0331-minio-quay-image
Created: 2026-09-15
Updated: 2026-09-15

## Goal

Make `docker compose -f docker-compose.prod.yml pull` succeed again so the
auto-deploy on `main` can complete instead of taking prod down.

## Problem

The deploy for PR #87 (merged 2026-09-15 10:57Z) **failed and left prod with no
containers** — `marinssolutions.com` answered 521 for ~40 minutes. The deploy
script runs `compose down` and then `compose pull`; the pull aborted with

```
Error response from daemon: pull access denied for minio/minio, repository does
not exist or may require 'docker login'
```

and `set -e` stopped the script before `build` and `up`. Docker Hub's
`minio/minio` is no longer pullable at all — the digest we pin
(`sha256:14cea493…`), `latest` and dated tags all fail `docker manifest
inspect` — while `quay.io/minio/minio` serves the identical release
(`RELEASE.2025-09-07T16-13-09Z`, verified from the running container's
`minio --version` and the local image labels). Nothing in the repo changed to
cause this; the upstream registry did.

Recovery performed by hand on the droplet: all eight data volumes and the
`.env` were intact, so the app tier was started on the still-local images
(`compose up -d --no-build --pull never postgres redis backend frontend nginx
certbot`), then the Langfuse tier the same way (the MinIO image was present
locally under its digest), and the new backend/frontend images were built
from the synced source and swapped in. The synced compose file on the droplet
was patched to the quay reference so the next `pull` succeeds.

## Scope

- `docker-compose.prod.yml`: `minio` and `minio-init` images →
  `quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z` (same release, pinned by
  tag, pullable).

## Non-Goals

- Reordering the deploy script so `pull`/`build` run **before** `down`. That
  ordering is what turned a pull failure into a full outage and deserves its
  own ticket; it is deliberately not bundled with this registry fix.
- Any other image pin.

## Acceptance Criteria

- [x] `docker compose -f docker-compose.prod.yml config --images` lists the
      quay reference for both `minio` and `minio-init`.
- [x] `docker compose -f docker-compose.prod.yml pull --dry-run minio` succeeds
      on the droplet (verified: "Pulled").
- [x] The pinned tag is the exact release currently running in prod.
- [ ] The next `main` deploy completes (`deploy.yml` green) — proven by the
      merge of this PR.

## Repro Steps

1. `docker manifest inspect minio/minio@sha256:14cea493d9a34af32f524e538b8346cf79f3321eff8e708c1e2960462bd8936e` → fails.
2. `docker manifest inspect quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z` → succeeds.

## Affected Areas

- [x] Backend (deploy config)
- [ ] Frontend
- [ ] Tests

## Dependencies

None. Follow-up: deploy-order ticket (pull/build before down).

## Progress Log

### 2026-09-15

Outage diagnosed from the deploy run log; prod restored by hand from local
images; compose pinned to quay in the repo and on the droplet.

## Files Touched

- `docker-compose.prod.yml`

## Test Evidence

Config/tooling change (AE-0153 no-`.feature` path): no user-visible behaviour
change — the identical MinIO release is served from a different registry.
Verification is the live dry-run pull on the droplet and `compose config`
listing both quay references. No static-analysis rule is added (AE-0180 N/A).

## QA Report

Pending.

## Blockers

None.
