# AE-0304 — remove stale unmanaged test containers and add prod container hygiene

Status: Ready
Tier: T1
Priority: Medium
Type: Chore
Area: Deployment
Owner: Unassigned
Branch: TBD
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

- [ ] Orphan status verified beyond compose: shell history, cron, systemd timers,
      and runbooks were grepped for the container names/endpoint and found no
      references (evidence recorded).
- [ ] `docker inspect` of both containers **and their volumes (incl. anonymous
      volumes)** is captured to a runbook artifact before removal; any non-empty
      volume is snapshotted (reversibility incl. stored data, not just config).
- [ ] For any non-empty volume, restorability is proven **off the prod box** (the 4GB
      droplet at 79% disk should not run a restore-demo container): copy the snapshot to
      a dev/laptop host and demonstrate mount → start container → read an object/row
      back. On prod itself, only a lightweight integrity check (hash + `mc ls` of the
      mounted volume). "We have the bytes" is not proof of restorability (a MinIO volume
      needs its keys + bucket metadata + a compatible binary to rehydrate).
- [ ] `minio-test` and `langfuse-worker-test` no longer exist
      (`docker ps -a` shows neither), and they do not come back after a reboot.
- [ ] `docker ps` shows only containers defined in `docker-compose.prod.yml`.
- [ ] Dangling images/build cache pruned; free disk on `/` measurably improved
      (record before/after `df -h /`).
- [ ] The production site and a carousel smoke still work after cleanup (no
      accidental removal of a real dependency).
- [ ] Deployment runbook documents the "only compose-managed containers in prod"
      hygiene rule.

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

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
