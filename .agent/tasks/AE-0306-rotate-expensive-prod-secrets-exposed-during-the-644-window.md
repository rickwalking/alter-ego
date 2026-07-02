# AE-0306 — rotate expensive prod secrets exposed during the 644 window

Status: Ready
Tier: T2
Priority: High
Type: Security
Area: Deployment
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-07-01
Updated: 2026-07-01

## Goal

Rotate the production secrets that were world-readable during the 644 window
(AE-0301) but are **too disruptive to rotate inline** — the ones whose rotation
invalidates sessions, needs a coordinated DB change, or can strand encrypted data —
each in its own controlled change window, with a deadline.

## Problem

AE-0301 found `/opt/alter-ego/.env` + `backend/.env` world-readable (mode 644) with
live secrets. AE-0301 rotates the cheap, zero-blast-radius API keys immediately. The
remaining secrets were exposed for the same window but cannot be rotated casually:

- `SECRET_KEY` / `ANON_SECRET_KEY` — rotation invalidates all existing sessions/
  signed tokens (users/anon sessions dropped); needs a comms/timing decision.
- `POSTGRES_PASSWORD` — must be changed on the DB **and** every consumer
  (`CAROUSEL_CHECKPOINT_POSTGRES_URL`, app DB URL, Langfuse's Postgres) atomically or
  the app loses DB access.
- `LANGFUSE_ENCRYPTION_KEY` / `LANGFUSE_SALT` — rotating the encryption key/salt can
  make previously-encrypted Langfuse data unreadable; needs a documented Langfuse
  key-rotation procedure (or an accept-loss decision).
- `LANGFUSE_NEXTAUTH_SECRET`, `LANGFUSE_CLICKHOUSE_PASSWORD`, `LANGFUSE_MINIO_PASSWORD`
  — service credentials that require restarting the dependent services together.

"Recorded a decision to accept" is not acceptable closure for live, exposed
credentials — hence a tracked ticket with a deadline rather than a decision-log line.

## Scope

- For each secret above: determine the safe rotation procedure (order of operations,
  which services restart, any data-migration/decrypt-then-reencrypt step), execute it
  in a maintenance window, update GitHub Secrets, and verify the stack post-rotation.
- **Postgres topology (verified 2026-07-01):** there is **one** Postgres container
  (`alter-ego-postgres-1`, `postgres:17-alpine`), **one** role (`rag_user` =
  `POSTGRES_USER`, not `postgres`), serving multiple databases — the app DB, the
  carousel checkpoint, and Langfuse's `langfuse` DB (Langfuse connects to
  `postgres:5432/langfuse` as `rag_user`). So `POSTGRES_PASSWORD` rotation is **one
  role's password change shared across all consumers**, not two credential stores —
  simpler than assumed, but the _consumer_ list is what matters (below). Re-confirm
  this topology at execution time before proceeding.
- **Enumerate every _consumer_ of the `rag_user` credential, not just the app
  services** — including `pg_dump`/backup scripts, cron/systemd timers, and manual ops
  runbooks. (Verified 2026-07-01: **no `pg_dump`/backup cron exists today** — root
  crontab and `/etc/cron.d` have only certbot/e2scrub/sysstat — so nothing existing
  breaks; the _absence of any DB backup_ is itself a gap worth a separate ticket.)
  Re-enumerate at execution time; each consumer found must be migrated and confirmed
  green post-rotation, or documented as retired.
- **Design the `POSTGRES_PASSWORD` rotation as a constructed, reversible procedure, not
  an asserted "atomic" step.** First **verify each consumer's reconnect behavior**: the
  compose services read the credential **once from `env_file` at container start** and
  do not hot-swap, and there is **no PgBouncer** in the stack — so the zero-downtime
  "new role / dual-credential" approach (option a) is **not available without new
  infra** and must not be attempted naively (a consumer holding the old DSN would
  split-brain: pass the smoke, fail later, then get stranded at revoke). Therefore the
  **default is (b): a deliberate, bounded downtime window with a full-stack restart**,
  stated up front; option (a) only if PgBouncer/dual-role infra is actually added
  first. Define **rollback as code**: do not revoke/drop the old password until a
  post-restart smoke confirms every consumer authenticates with the new one; gate on a
  confirmed role state before revoking. Sequence inside the AE-0303 auto-reboot lock so
  a reboot (or a coincident `main` auto-deploy) cannot fire mid-rotation and strand the
  stack on _neither_ password.
- **First establish whether the installed Langfuse version (verified: `3.185`)
  actually supports encryption-key rotation with re-encryption of existing data.** If
  it does not, then
  "rotate `LANGFUSE_ENCRYPTION_KEY`/`SALT`" is really an _accept-loss-of-historical-
  encrypted-data_ decision — it must be surfaced and signed off as such, not
  hand-waved as "documented procedure." Old-data readability must be tested, not
  assumed from a clean cold start.
- Sequence relative to the reboot/lockdown tickets so rotations do not collide with
  AE-0303 (reboot) or AE-0300 (origin lockdown).
- Record the exposure-window estimate (carried from AE-0301) as the justification.

## Non-Goals

- Not the cheap API-key rotation (done in AE-0301).
- Not migrating to a secrets manager (separate initiative).
- Not changing the app's auth/session design — only rotating the key values.

## Acceptance Criteria

- [ ] Before rotating `SECRET_KEY`/`ANON_SECRET_KEY`, **enumerate in-flight state
      signed/validated by them** — carousel checkpoints, WebSocket/SSE auth tokens, anon
      session cookies — and define the transition: either **drain first** (no in-flight
      carousel generation during the window) or a **dual-key validation window**. A
      carousel mid-generation whose checkpoint is HMAC-bound to the old key must not be
      silently stranded. ("Login + anon flows work post-rotation" covers the after
      state, not the transition of in-flight work.)
- [ ] `SECRET_KEY` and `ANON_SECRET_KEY` rotated; new values live via GitHub Secrets;
      the impact (session/token invalidation) was scheduled/communicated and verified
      (login + anon flows work post-rotation; no in-flight carousel stranded).
- [ ] Every Postgres instance and its credential source is enumerated (app DB vs a
      possibly-separate Langfuse Postgres); the rotation AC is **split per instance** so
      none is left unrotated.
- [ ] Every **consumer** of each instance's password is enumerated (app services +
      `pg_dump`/backup crons + ops scripts) and confirmed green post-rotation (or
      documented as retired) — a failing backup cron must not go silently unnoticed.
- [ ] **A `pg_dump` (or verified snapshot) is taken immediately before
      `POSTGRES_PASSWORD` rotation and stored off-box** — since no backup cron exists,
      a rotation that bricks connectivity in a way the smoke misses would otherwise be
      irrecoverable without data loss.
- [ ] **In-flight DB-dependent work is drained** (mirroring the session-key AC): no
      in-flight carousel generation during the full-stack-restart rotation window, OR
      idempotent checkpoint resume is proven to survive a forced mid-write DB
      disconnect — so the restart cannot silently corrupt/strand a carousel's
      checkpoint stream.
- [ ] `POSTGRES_PASSWORD` rotation uses a **defined design** — either dual-credential/
      new-role zero-downtime OR a bounded, deliberate downtime window (stated up front)
      — with **rollback as code**: the old password is revoked only after a post-change
      smoke confirms every consumer authenticates with the new one; a mid-rotation
      failure has a documented recovery (not "un-rotate," which is impossible). The app,
      carousel checkpointing, and Langfuse all reconnect (no
      `password authentication failed` in logs).
- [ ] The installed Langfuse version's key-rotation/re-encryption capability is
      established and recorded.
- [ ] `LANGFUSE_ENCRYPTION_KEY`/`SALT` handled per that capability, with the AC
      **split**: (a) new traces write and read correctly after rotation, AND
      (b) pre-rotation traces remain readable — OR, if re-encryption is unsupported,
      an **explicit accept-loss-of-historical-data decision is recorded and signed
      off** (the "still starts" check alone must not mask silent old-data loss).
- [ ] `LANGFUSE_NEXTAUTH_SECRET`, `LANGFUSE_CLICKHOUSE_PASSWORD`,
      `LANGFUSE_MINIO_PASSWORD` rotated with the dependent services restarted together
      and verified healthy.
- [ ] Old secret values are revoked/invalidated everywhere they were valid.
- [ ] A completion date is recorded (the deadline is met or an explicit extension is
      logged).

## Gherkin Scenarios

```gherkin
Feature: rotate exposed high-blast-radius production secrets safely

  Scenario: database password rotation keeps the stack connected
    Given POSTGRES_PASSWORD is rotated on the database and in GitHub Secrets
    When the stack is redeployed
    Then the backend, carousel checkpointing, and Langfuse all reconnect
    And no authentication-failed errors appear in the logs

  Scenario: session-signing key rotation is scheduled, not surprise
    Given SECRET_KEY / ANON_SECRET_KEY rotation invalidates existing sessions
    When the rotation is performed in the planned window
    Then users can re-authenticate and anon sessions re-initialize normally

  Scenario: a failed database password rotation has a defined recovery
    Given a POSTGRES_PASSWORD rotation is in progress
    When a consumer redeploy fails before it reads the new password
    Then the old password has not yet been revoked
    And the documented recovery restores authentication without a second blind rotation
    And no unattended-upgrades reboot fires while the rotation lock is held
```

## Delta

### ADDED

- New values for the expensive secrets in GitHub Secrets; documented rotation
  procedures per secret.

### MODIFIED

- GitHub Secrets; deploy `.env` (rewritten on deploy); no application code changes
  expected beyond config.

### REMOVED

- The exposed (pre-rotation) secret values, revoked at their sources.

## Affected Areas

- Backend: DB URL / SECRET_KEY / ANON_SECRET_KEY consumers
- Frontend: none (server-side secrets)
- Database: Postgres password change
- API: none directly
- Tests: post-rotation smoke (login, anon, carousel, Langfuse) — mostly runtime verification
- Docs: per-secret rotation procedures in `docs/deployment/`
- Prompts/LLM: none
- Observability: Langfuse encryption-key/salt handling; ClickHouse/MinIO creds
- Deployment: maintenance window; GitHub Secrets update + redeploy

## Dependencies

- Blocks: none
- Blocked by: AE-0301 (exposure-window estimate + cheap-key rotation land first) **and
  AE-0303** (the lock landlord — AE-0303 defines the shared rotation/reboot lock's
  path/holder/TTL/force-clear; this rotation _consumes_ that lock, so it must not land
  before the lock exists, or it would run unguarded / invent a divergent lock).
- Related: AE-0303 (reboot window), AE-0300 (origin lockdown) — coordinate windows
- Deadline: within 14 days of AE-0301 landing (by 2026-07-15) unless an extension is
  logged with rationale.

## Implementation Plan

1. Pull the exposure-window estimate from AE-0301 as justification.
2. Draft the per-secret rotation runbook (order, restarts, data handling).
3. Rotate in a maintenance window (DB password + consumers atomically; Langfuse keys
   per its procedure; session keys with scheduling).
4. Verify the full stack; revoke old values; record completion date.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (partial rotation rollback, Langfuse data readability)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-07-01

Spun out of AE-0301 per skeptical review R2 (GLM 5.2): the high-blast-radius exposed
secrets need a tracked ticket with a deadline rather than an accept-the-risk line.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- 2026-07-01: Split from AE-0301 so exposed secrets are all _tracked to rotation_,
  while keeping the disruptive rotations in a controlled window separate from the
  quick file-permission remediation.
- 2026-07-01 (skeptical review R3, GLM 5.2): WARN "Langfuse key rotation may be
  unrecoverable, not just 'needs a procedure'" → **accepted**: added an AC to first
  establish the installed version's re-encryption capability, split the readability AC
  (new vs pre-rotation data), and require an explicit signed-off accept-loss decision
  if re-encryption is unsupported. Rotation windows must also avoid AE-0303
  auto-reboot firing mid-rotation (see AE-0303 reboot-lock).
- 2026-07-01 (skeptical review R4, GLM 5.2): BLOCKER "'atomic' Postgres rotation has no
  rollback/downtime design" → **accepted**: rotation is now a constructed procedure
  (dual-credential/new-role OR bounded deliberate downtime), rollback-as-code
  (revoke-after-smoke, gate on role state), sequenced inside the AE-0303 reboot lock,
  with a Gherkin failure scenario. WARN "one Postgres or two?" → **accepted**: enumerate
  every Postgres instance + credential source first and split the AC per instance.
- 2026-07-01 (skeptical review R5, GLM 5.2): WARN "enumerate ops/backup consumers, not
  just app services" → **accepted**: added an AC to enumerate `pg_dump`/backup/cron/ops
  consumers of each Postgres credential and confirm each green post-rotation (a silent
  backup failure is data-loss risk).
- 2026-07-01 (skeptical review R6, GLM 5.2): WARN "zero-downtime option (a) needs
  PgBouncer/dual-role not in the stack" → **accepted**: verified compose reads creds
  once at startup with no PgBouncer, so **(b) bounded downtime + full-stack restart is
  the default**; (a) only if that infra is added first — removing the split-brain risk
  from a naive (a).
- 2026-07-01 (skeptical review R7, GLM 5.2): WARN "session-key rotation omits in-flight
  signed state" → **accepted**: added an AC to enumerate carousel-checkpoint/WebSocket/
  anon state bound to `SECRET_KEY`/`ANON_SECRET_KEY` and drain-first-or-dual-key the
  transition. Also grounded the ticket with verified facts (one Postgres/one `rag_user`
  role, no PgBouncer, no backup cron, Langfuse 3.185), retiring several
  missing-evidence items.
- 2026-07-01 (skeptical review R8, GLM 5.2): WARN "no in-flight-drain AC for POSTGRES
  (only session keys)" → **accepted**: mirrored the drain AC for the DB rotation
  (drain carousels or prove idempotent resume across the restart). WARN "no
  pre-rotation backup despite no backup cron" → **accepted**: added a pre-rotation
  `pg_dump`-off-box AC so a rotation incident is recoverable.
- 2026-07-01 (skeptical review R9, GLM 5.2): WARN "consumes AE-0303's lock but isn't
  `Blocked by` it (could land first and run unguarded)" → **accepted**: added a hard
  `Blocked by: AE-0303`, so the lock exists before this rotation uses it.

## Blockers

None.

## Final Summary

Pending.
