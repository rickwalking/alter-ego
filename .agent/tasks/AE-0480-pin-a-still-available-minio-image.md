# AE-0480 — Pin a still-available MinIO image for the Langfuse stack

Status: Done
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Worker (Claude)
Agent Lane: developer → qa → release
Branch: fix/ae-0480-minio-image
Kanban Card: TBD
Created: 2026-10-22
Updated: 2026-10-22

## Goal

The production `minio` and `minio-init` services reference an image that a fresh droplet can pull anonymously,
pinned by tag and digest so it cannot change or disappear without a commit.

## Problem

The prod deploy log shows `quay.io/minio/minio` returning 401: MinIO, Inc. withdrew the image (Docker Hub
`minio/minio` was already gone, AE-0331). Prod still runs because the image is cached on the droplet, but the
deploy prunes images older than 168h and a new droplet has no cache, so the next fresh pull breaks Langfuse
(event uploads go to MinIO).

Evidence, 2026-10-22, from a workstation (anonymous):

```text
$ docker manifest inspect quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z
no such manifest: quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z
$ curl https://quay.io/v2/minio/minio/manifests/RELEASE.2025-09-07T16-13-09Z   (with an anonymous pull token)
HTTP 401 {"errors":[{"code":"UNAUTHORIZED","message":"access to the requested resource is not authorized"}]}
$ docker manifest inspect docker.io/minio/minio:RELEASE.2025-09-07T16-13-09Z
denied: requested access to the resource is denied / unauthorized: authentication required
$ docker manifest inspect mirror.gcr.io/minio/minio@sha256:14cea493...36e
no such manifest
```

Prod, read-only (`docker compose images minio`, `docker image inspect`):

```text
alter-ego-minio-1   quay.io/minio/minio   RELEASE.2025-09-07T16-13-09Z   linux/amd64   14cea493d9a3   62.2MB
[quay.io/minio/minio@sha256:14cea493d9a34af32f524e538b8346cf79f3321eff8e708c1e2960462bd8936e] 2025-09-07T18:42:37Z
minio version RELEASE.2025-09-07T16-13-09Z (commit-id=07c3a429bfed433e49018cb0f78a52145d4bedeb)
```

## Options checked

- Same release elsewhere: not published anywhere reachable (quay 401, Docker Hub denied, mirror.gcr.io no
  manifest, public.ecr.aws no repo, `bitnami/minio` empty, `bitnamilegacy/minio` frozen at 2025.7.23).
- `cgr.dev/chainguard/minio` (used by Langfuse's own compose): free tier serves `latest` only, no release tags.
- **Chosen:** `docker.io/pgsty/minio:RELEASE.2026-08-04T00-00-00Z@sha256:b6bfe7239bfc83fb90d31612d9704d86039dd714f7904b3f1ad68f211e602372`
  (multi-arch OCI index, amd64 + arm64). Pigsty's community fork of `minio/minio` (GitHub `pgsty/minio`, now
  `pgsty/silo`), AGPLv3 like upstream, actively released (latest 2026-10-18), 2.4M pulls. `RELEASE.2026-08-04` is
  its last release under the MinIO name: same `minio` binary, `MINIO_*` env, entrypoint, `/data` layout and bundled
  `mc`, so `minio-init` works unchanged. Later releases rename the product (Silo, `mcli`); moving to them is a
  separate decision.
- Langfuse documents any S3-compatible store through `LANGFUSE_S3_*` (MinIO, AWS S3, R2, GCS, Azure). Leaving
  the self-hosted store would need a data migration and new secrets, so it is not done here.

## Scope

- `docker-compose.prod.yml`: `minio` and `minio-init` pinned to the chosen tag@digest. Command, volume, env and
  credentials unchanged.
- Regression guard: a unit test asserting both services are pinned by tag@sha256, use the same reference, never
  reference `quay.io/minio` or Docker Hub `minio/minio`/`minio/mc`, and keep `server /data`, `minio_data:/data` and the
  `langfuse` root user.

## Non-Goals

- The dev `docker-compose.yml` (`minio/minio:latest`, `minio/mc:latest`) stays with AE-0345.
- Digest-pinning the other prod images.
- Moving to the Silo-named releases or to an external S3 provider.

## Acceptance Criteria

- [x] Both MinIO services reference `docker.io/pgsty/minio:RELEASE.2026-08-04T00-00-00Z@sha256:b6bfe723…2372`.
- [x] The digest pulls anonymously (verified with `docker pull` from a workstation).
- [x] Data written by an older upstream MinIO (2025-07-23) is listed and read back by the new image on the same
      volume, and `mc mb -p local/langfuse-events` stays idempotent.
- [x] The prod `minio` + `minio-init` pair comes up from `docker-compose.prod.yml` in a throwaway project:
      `minio-init` exits 0 after creating `langfuse-events`, `minio` uses 72MiB of its 256M limit.
- [x] The guard test fails on the previous compose (quay tag) and passes on the new one.
- [x] The next deploy pulls the new image, recreates `minio`, and Langfuse traces still upload. Verified 2026-10-22
      11:06Z: prod runs `docker.io/pgsty/minio@sha256:b6bfe723…`, buckets intact, Langfuse up. The old quay image is
      no longer cached on the droplet.

## Gherkin Scenarios

- `backend/tests/features/compose_object_storage_image_ae0480.feature`

## Affected Areas

- Infra: `docker-compose.prod.yml`
- Tests: `backend/tests/unit/scripts_ci/`

## Dependencies

- Related: AE-0331 (moved to quay), AE-0344 (quay digest pin, superseded by this ticket), AE-0345 (dev compose)

## Deploy notes

The deploy runs `compose pull` before `down`, so the new image is fetched first and `up -d` recreates `minio` and
`minio-init` on it. Data persists: the named volume `minio_data` is reused, and the fork reads the upstream on-disk
format. Rollback to the cached quay image works only while the droplet still has it; after a prune it is gone.

## QA Checklist

- [x] Security reviewed
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-22

Confirmed the 401 on quay and the denial on Docker Hub, read the running image on prod (read-only), surveyed
mirrors, chose `pgsty/minio` pinned by tag@digest, tested data compatibility and the prod service pair locally,
added the compose guard test.

## Files Touched

- docker-compose.prod.yml
- backend/tests/features/compose_object_storage_image_ae0480.feature
- backend/tests/unit/scripts_ci/test_compose_object_storage_image_ae0480.py
- .agent/tasks/AE-0480-pin-a-still-available-minio-image.md

## Final Summary

Merged as #209 and deployed: prod's Langfuse stack runs `docker.io/pgsty/minio@sha256:b6bfe723…` (recreated
2026-10-22 11:06Z), buckets intact, Langfuse up. AE-0344 (re-pin by quay digest) is superseded by this ticket.
