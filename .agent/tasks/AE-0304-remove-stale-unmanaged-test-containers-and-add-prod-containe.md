# AE-0304 — remove stale unmanaged test containers and add prod container hygiene

Status: Review
Tier: T1
Priority: Medium
Type: Chore
Area: Deployment
Owner: Claude (developer-skill)
Branch: feat/ae-0300-0307-prod-security
Created: 2026-07-01
Updated: 2026-07-01

## Goal

Remove the orphaned `*-test` containers running on production and reclaim disk, so
the only long-running containers on the droplet are the ones defined in
`docker-compose.prod.yml`.

## Problem

The 2026-07-01 security scan found two unmanaged containers running on production
since 2026-06-12 with `restart=unless-stopped`, i.e. they survive reboots and
nobody is watching them:

```
minio-test            image=minio/minio                created 2026-06-12  restart=unless-stopped  user=root
langfuse-worker-test  image=langfuse/langfuse-worker:3 created 2026-06-12  restart=unless-stopped
```

These are not part of `docker-compose.prod.yml`. They are unmonitored attack
surface (a test MinIO commonly ships default `minioadmin:minioadmin` credentials
and sits on the same Docker network as the real services — see AE-0302), they
consume RAM/CPU/disk on a 4 GB box already at 79% disk (91 G/116 G), and they
confuse the running-state picture. They should be removed unless there is a
documented reason to keep them.

## Scope

- Confirm the two `*-test` containers are genuinely orphaned. Absence from
  `docker-compose.prod.yml` is necessary but **not sufficient** — also grep shell
  history, cron, systemd timers, and any operator runbooks for the container names
  and the `minio-test` endpoint before removing.
- **Before removal, capture `docker inspect` (image, env, mounts, network, command)
  for both containers into a runbook artifact** so they can be recreated if a
  hidden dependency surfaces (`docker rm -f` is not reversible without this).
- **Also inspect the containers' volumes — including anonymous volumes** (not just
  named mounts) — and snapshot any that are non-empty before removal. `docker inspect`
  captures config but not stored data; a `minio-test` may hold objects in an
  anonymous volume that `rm -f` would orphan/lose. Record volume contents (or confirm
  empty) as part of the reversibility artifact.
- `docker rm -f minio-test langfuse-worker-test`.
- Prune dangling images/build cache to reclaim disk (`docker image prune`, and
  review the duplicate `langfuse-worker:3` / `:3.185` and `minio` tags).
- Document a hygiene note: production should run only compose-managed containers;
  ad-hoc test containers must be removed after use (add to the deployment runbook).

## Non-Goals

- Not removing any compose-managed production container.
- Not changing MinIO/Langfuse versions or config for the real services.
- Not adding an automated reaper/cron (documentation + one-time cleanup is enough
  for now; propose automation only if this recurs).

## Acceptance Criteria

- [x] Orphan status verified beyond compose: shell history (0 refs), root crontab,
      /etc/cron.\*, /etc/systemd/system all clean; creator identified as the ad-hoc
      `compose.langfuse-s3-test.yml` (2026-06-12 debugging leftover); timer set
      enumerated (evidence in docs/deployment/ae-0304-orphan-container-removal.md).
- [x] `docker inspect` of both containers **and their volumes (incl. anonymous
      volumes)** is captured to a runbook artifact before removal; any non-empty
      volume is snapshotted (`/root/env-backups/ae-0304/`: 2 inspect JSONs +
      `minio_test_data.tar.gz` sha256 6d3acfbf…4077a21; worker had no mounts).
- [x] For any non-empty volume, restorability is proven **off the prod box**: snapshot
      copied to the dev host (sha256 verified), mounted into a fresh `minio/minio` with
      the original root creds from the inspect artifact, `mc ls -r` listed all 6
      objects, `mc cat` read an object back intact. (Discovered + recorded: MinIO root
      creds live in container env, so the inspect artifact is required to rehydrate.)
- [x] `minio-test` and `langfuse-worker-test` no longer exist
      (`docker ps -a` shows neither); nothing can recreate them (the restart policy
      died with the containers; no compose/cron/systemd reference remains) — the
      AE-0303 reboot doubles as the live confirmation.
- [x] `docker ps` shows only containers defined in `docker-compose.prod.yml`.
- [x] Dangling images/build cache pruned (~1G: the floating `langfuse-worker:3`);
      `df -h /`: 91G/79% → 90G/78%. (`minio/minio:latest` kept — same digest the
      compose-managed MinIO pins.)
- [ ] The production site and a carousel smoke still work after cleanup (no
      accidental removal of a real dependency). **Partially done**: site 200, backend
      /health 200, Langfuse health 200, real langfuse-worker-1 executing jobs
      post-cleanup. The carousel-specific smoke needs an authenticated prod run —
      open for the operator (removed containers are not on the carousel path).
- [x] Deployment runbook documents the "only compose-managed containers in prod"
      hygiene rule (DEPLOYMENT_GUIDE §9 + ae-0304-orphan-container-removal.md).

## Repro Steps

1. `ssh root@<origin>`; `docker ps --format '{{.Names}} {{.Image}} {{.Status}}'`.
2. Observe `minio-test` and `langfuse-worker-test` `Up 2 weeks`, not in any compose file.
3. `df -h /` → 79% used.

## Affected Areas

- [ ] Backend
- [ ] Frontend
- [ ] Tests
- Deployment: remove orphaned containers, prune images, runbook hygiene note
- Ops: same Docker network as production services (lateral-risk context for AE-0302)

## Dependencies

- Blocks: none
- Blocked by: none
- Blocks: **AE-0303** (this cleanup + a soak must complete before the AE-0303 reboot —
  a hard gate, mirrored by `Blocked by: AE-0304` on AE-0303, so the two cannot land
  the same day). **Soak = ≥24h wall-clock AND every daily-cycle cron/systemd timer
  has fired at least once against the post-removal state** (a lazy daily job that
  calls the `minio-test` endpoint would otherwise surface only at the reboot). Verify
  the daily jobs actually ran, don't treat 24h as a pure wall-clock proxy. The soak
  check is "every timer in the **enumerated cron/systemd list** fired" — that list is
  the artifact produced by the orphan-grep step above and is referenced by this AC
  (a soak means nothing without knowing the timer set it is measured against). Note
  this still does not cover weekly/monthly dependents — the `docker inspect`/volume
  snapshot artifact is the reversibility backstop for those.
- Related: AE-0302 (unauth Redis + unmanaged containers on one network)

## Decision Log

- 2026-07-01 (skeptical review, GLM 5.2 — `.agent/reports/AE-0300-0305.skeptical-review.md`):
  WARN "cleanup may remove an undeclared dependency with no rollback" → **accepted**:
  added history/cron/systemd/runbook grep to the orphan check, a pre-removal
  `docker inspect` capture for reversibility, and sequencing before the AE-0303
  reboot with a soak day.
- 2026-07-01 (skeptical review R2, GLM 5.2): WARN "`docker inspect` misses volume
  data / soak not enforced" → **accepted**: added anonymous-volume inspection +
  snapshot of non-empty volumes, and promoted the soak-before-reboot to a hard
  `Blocks: AE-0303` gate.
- 2026-07-01 (skeptical review R3, GLM 5.2): INFO "24h soak is a wall-clock proxy" →
  **accepted**: redefined the soak as ≥24h **and** every daily cron/systemd timer
  having fired once against the post-removal state.
- 2026-07-01 (skeptical review R4, GLM 5.2): INFO "soak only means something against an
  enumerated timer set" → **accepted**: the orphan-grep's cron/systemd enumeration is
  the referenced artifact the soak AC measures against; weekly/monthly dependents are
  backstopped by the inspect/volume-snapshot reversibility artifact.
- 2026-07-01 (skeptical review R5, GLM 5.2): WARN "snapshot is captured but not verified
  restorable" → **accepted**: added an AC to demonstrate a restore once (mount → start →
  read back) before the destructive `rm -f`.
- 2026-07-01 (skeptical review R6, GLM 5.2): WARN "restore-demo is resource-heavy on the
  4GB prod box" → **accepted**: the full restore-demo runs **off-box** (dev/laptop) from
  the snapshot; on prod only a lightweight hash + `mc ls` integrity check.
- QA classification (CLAUDE.md CI/config path, AE-0153): ops/runtime container
  removal with no in-repo behavior to `.feature`-test; verification is the documented
  `docker ps -a`/`docker inspect`/`df -h` evidence + post-cleanup smoke captured in
  the gate log, plus the runbook hygiene note. No `.feature` claimed; QA signs off.

## Implementation Plan

1. Verify the two containers are not referenced by any compose/staging file.
2. `docker rm -f minio-test langfuse-worker-test`.
3. `docker image prune` (+ review duplicate langfuse/minio tags); record `df -h /`
   before/after.
4. Smoke-test the site + a carousel run.
5. Add the hygiene note to `docs/deployment/`.

## Progress Log

### 2026-07-01

Ticket created from the 2026-07-01 production security scan (finding #5, MEDIUM).

### 2026-07-02 — executed (developer-skill)

- Investigation found the containers were NOT inert: `langfuse-worker-test` ran a
  floating `:3` tag **live against the real Postgres/Redis/ClickHouse** while
  pointing S3 uploads at `minio-test:9000` — a second, version-drifting worker on
  the real queue writing blobs to the wrong MinIO. Removal is a data-integrity fix.
- **Security finding**: the creator file `compose.langfuse-s3-test.yml` sat in
  `/opt/alter-ego` with the **real `LANGFUSE_MINIO_PASSWORD` in plaintext**;
  relocated to `/root/env-backups/ae-0304/` (600) and the secret added to the
  AE-0301 cheap-rotation list.
- Sequence executed: stop → inspect JSONs + volume tar (sha256) → off-box restore
  demo proven → `rm -f` both → `volume rm minio_test_data` → prune (~1G) →
  smoke green. Full record: `docs/deployment/ae-0304-orphan-container-removal.md`.
- **Soak for AE-0303 started 2026-07-02 ~04:00 UTC** — reboot allowed after ≥24h
  AND every enumerated daily timer fires once (list in the removal record).

## Files Touched

- `docs/deployment/ae-0304-orphan-container-removal.md` — new removal/reversibility record
- `docs/deployment/ae-0301-key-rotation-runbook.md` — `LANGFUSE_MINIO_PASSWORD` row added
- `docs/deployment/DEPLOYMENT_GUIDE.md` — §9 compose-managed-only hygiene item
- Droplet (not in git): containers + volume removed; artifacts in `/root/env-backups/ae-0304/`

## Test Evidence

```
docker ps -a | grep test           → (nothing)
df -h /                            → 79% → 78% (91G → 90G)
site 200 / backend health 200 / langfuse health 200 / worker-1 executing jobs
restore demo (dev host): mc ls → 6 objects; mc cat test-evt-minio.json → intact
sha256(minio_test_data.tar.gz) = 6d3acfbfddfbf2571e141db897b20896c8b8c2242f46aa44ebee3afea4077a21
```

## QA Report

External QA (opencode-go/glm-5.2): **WARN, 0 blockers** — both warnings are
operator/CI-time items (carousel smoke; SKIP gates green-by-construction on a
docs-only diff). AE-0153 no-.feature classification signed off; soak-gate
coherence and no-secret-leak grep verified by the reviewer. Report:
`.agent/reports/AE-0304.qa.md`. Open operator items tracked in its addendum.

## Blockers

None.
