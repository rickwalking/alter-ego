# AE-0303 — apply pending os security updates and reboot droplet in a maintenance window

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

Bring the production droplet current on OS/library/kernel patches and reboot it in
a maintenance window so pending kernel/library fixes actually take effect, then
configure automatic reboots so the box does not drift again.

## Problem

The 2026-07-01 security scan found the droplet behind on patches and needing a
reboot:

```
apt-get -s upgrade | grep -c '^Inst'          → 54 upgradable packages
/var/run/reboot-required                        → present since Jun 3
uname -r                                         → 6.8.0-71-generic (uptime 64 days)
```

`unattended-upgrades` is active, but the reboot-required flag has been set since
Jun 3, meaning kernel/library updates are downloaded but **not live** — a running
kernel and in-memory libraries from before Jun 3 do not benefit from any fixes
shipped since. 54 upgradable packages is a meaningful backlog. A reboot restarts
the Docker containers (~short blip), so it needs a maintenance window.

## Scope

- Run `apt-get update && apt-get upgrade` (and `dist-upgrade` if needed for kernel)
  on the droplet.
- Reboot the droplet in a maintenance window; verify all containers come back
  healthy (note: `alter-ego-frontend-1` was already reporting `unhealthy` pre-reboot
  — confirm whether that clears or needs separate attention).
- **Before rebooting:** verify **every** prod compose service has a
  `restart: unless-stopped` (or `always`) policy — this is the precondition the
  auto-reboot path depends on; if any service lacks it, add it. Capture the policies
  and the frontend healthcheck definition, and **root-cause the pre-existing
  `alter-ego-frontend-1` unhealthy state** (or explicitly de-scope it into a
  referenced follow-up ticket — not an open-ended "track separately").
- **Coordinate auto-reboot with app/deploy state, and OWN the shared lock's
  lifecycle.** `unattended-upgrades` auto-reboot is ungated by default and could fire
  mid-deploy (partial `.env` write), during a running carousel (WebSocket/SSE), or
  mid-rotation (AE-0301/AE-0306) — a corrupting event, not the intended blip. This
  ticket (the reboot owner) **defines the single lock file** that deploy, rotation
  (AE-0306), and the CF-range refresh (AE-0300) all reference: its **path, holder
  identity, TTL/watchdog, staleness detection, force-clear procedure, and
  revert-on-holder-crash** behavior. This matters because a stale lock (holder crashed
  mid-rotation) would otherwise silently disable the auto-reboot safety net forever, or
  a wrongly force-cleared lock lets a reboot fire mid-rotation. The auto-reboot skips
  while the lock is held; **do not enable auto-reboot until AE-0306 rotation is
  complete**.
- **Define the `main`-push auto-deploy's lock interaction explicitly** — it is the
  primary automated mutator and is triggered outside any lock-holder's control. The
  `deploy.yml` job must **acquire the lock or fail closed with an operator-visible
  message** (not hang indefinitely), OR a **deploy-freeze** (branch protection / a
  required-reviewer GitHub Environment / a freeze flag the deploy checks first) holds
  `main` deploys during rotation/reboot windows. Pick one and encode it, so a
  `git push origin main` mid-rotation cannot silently race the lock (deploy proceeds =
  invariant false) or hang CI into a panic force-cancel (the exact compound failure the
  lock exists to prevent).
- Configure `unattended-upgrades` automatic reboot (`Unattended-Upgrade::Automatic-Reboot "true";`)
  with an `Automatic-Reboot-Time` chosen from a **named, pre-verified traffic-data
  source**. Cloudflare zone analytics is preferred **only if actually queryable** —
  its GraphQL analytics API needs a token with `Zone.Analytics` scope and a plan with
  sufficient retention; confirm the token/endpoint works _before_ adopting it. If it
  is not available, use nginx access logs and **say so up front** (don't let the
  fallback silently become the source). Record the actual query/screenshot used. Add a
  post-reboot smoke whose
  **failure alerts to a named sink** (the existing ops alert channel; if none exists,
  the minimum is an email to the admin) — do not leave the sink unspecified.
- **Wire the lock to the reboot actor concretely** — `unattended-upgrades` has no
  native app-lock concept, so specify the bridge: either disable
  `Unattended-Upgrade::Automatic-Reboot` and run a **cron + lock-aware reboot script**
  (checks the lock, reboots only if unheld and `reboot-required` is set), or add an
  `/etc/apt/apt.conf.d/99-lock-guard` (`DPkg::Pre-Invoke`/`Pre-Install-Pkgs`) that
  exits non-zero while the lock is held. Add it as an implementation step and an AC
  that proves a held lock blocks the reboot path (tested without a real mid-rotation
  reboot, e.g. dry-run the script with the lock present).
- **Slip-escalation for the AE-0306 gate:** since auto-reboot stays off until AE-0306
  completes and AE-0306 has a deadline with an extension escape hatch, gate
  auto-reboot-enable on **AE-0306 close OR a logged extension with a re-baseline
  date**; if the extension lapses, enable auto-reboot anyway with the rotation-safe
  default (lock honored) so the droplet does not silently re-drift indefinitely.
- Confirm `/var/run/reboot-required` is cleared afterward.

## Non-Goals

- Not upgrading the Ubuntu release (24.04 LTS stays).
- Not changing the Docker/compose stack or app versions.
- Not fixing the frontend container's `unhealthy` healthcheck as part of this
  ticket unless the reboot surfaces it as blocking (track separately if it persists).

## Acceptance Criteria

- [ ] `apt-get -s upgrade | grep -c '^Inst'` is ~0 after patching (only
      intentionally-held packages remain).
- [ ] The droplet has been rebooted; `uptime` reflects the recent reboot and
      `uname -r` shows the current kernel.
- [ ] `/var/run/reboot-required` is absent after the reboot.
- [ ] All production containers **except any explicitly de-scoped one** are
      `Up`/`healthy` after reboot (nginx, backend, postgres, redis, langfuse,
      clickhouse, minio, certbot) — the site serves 200 through Cloudflare and a
      carousel smoke passes. The pre-existing-unhealthy `frontend` is de-scoped: it is
      tracked as its own follow-up ticket with a stated reason it was unhealthy before
      the reboot, and the AC here is only that **the reboot did not worsen it** (same
      health state before and after) — not "frontend healthy". This removes the
      contradiction between "all healthy" and the de-scope clause.
- [ ] `unattended-upgrades` is configured to auto-reboot with an
      `Automatic-Reboot-Time` justified by a **named traffic-data source** (Cloudflare
      analytics / nginx logs — the evidence is recorded).
- [ ] **Every** prod compose service has a restart policy (verified list), so the
      auto-reboot case mirrors the manual-reboot verification; the frontend
      `unhealthy` state is either resolved or de-scoped into a referenced follow-up
      ticket before the reboot.
- [ ] The post-reboot smoke's **alert sink is named** and a failure demonstrably
      reaches it (not an unspecified "alerts on failure").
- [ ] Auto-reboot is **coordinated with deploy/rotation**: it does not fire while a
      deploy or a secret rotation is in flight (lock-file honored, or auto-reboot
      enabled only after AE-0306 completes).
- [ ] The shared lock file's lifecycle is **defined and owned here** (path, holder,
      TTL/watchdog, staleness detection, force-clear, revert-on-holder-crash); a
      holder crash leaves a deterministic, tested recovery (no permanently-stale lock
      that silently disables auto-reboot).
- [ ] The `main`-push auto-deploy's lock behavior is **explicitly defined** (acquire-
      or-fail-closed with an operator-visible message, or a deploy-freeze that holds
      `main` during rotation/reboot windows) — a push mid-rotation cannot silently race
      the lock or hang CI.
- [ ] A **concrete lock→reboot bridge** is implemented (cron+lock reboot script or an
      apt.conf.d guard hook) and a test proves a held lock blocks the reboot path.
- [ ] Auto-reboot-enable is gated on **AE-0306 close or a logged extension with a
      re-baseline date**; a lapsed extension enables auto-reboot with the rotation-safe
      (lock-honored) default so drift-prevention cannot be silently disabled forever.

## Repro Steps

1. `ssh root@<origin>`; `ls /var/run/reboot-required` → present since Jun 3.
2. `apt-get -s upgrade | grep -c '^Inst'` → 54.
3. `uptime` → 64 days (running pre-Jun-3 kernel).

## Affected Areas

- [ ] Backend
- [ ] Frontend
- [ ] Tests
- Deployment: OS patch level, kernel, `unattended-upgrades` reboot config
- Ops: requires a maintenance window (reboot restarts all containers)

## Dependencies

- Blocks: none
- Blocked by: **AE-0304** (container cleanup + its 24h soak must complete before this
  reboot, so the irreversible reboot does not compound with the removal of a
  possibly-depended-on container) — a hard gate, mirrored by `Blocks: AE-0303` on
  AE-0304.
- Related: memory `do-droplet-prod-deploy`

## Decision Log

- 2026-07-01 (skeptical review, GLM 5.2 — `.agent/reports/AE-0300-0305.skeptical-review.md`):
  WARN "reboots a box with a known unhealthy frontend + unvalidated auto-reboot
  timing" → **accepted**: added pre-reboot restart-policy/healthcheck capture,
  frontend root-cause-or-de-scope AC, traffic-justified `Automatic-Reboot-Time`, and
  a post-reboot smoke. WARN "cleanup+reboot compound with no rollback" → **accepted**:
  sequenced AE-0304 before this reboot (a reboot is irreversible, so de-risk first).
- 2026-07-01 (skeptical review R2, GLM 5.2): WARN "traffic data may not exist / alert
  sink unspecified / restart policy not a precondition" → **accepted**: named
  Cloudflare analytics (nginx fallback) as the traffic source, named the smoke alert
  sink, and made "every service has a restart policy" an explicit precondition AC.
  WARN "soak gap not enforceable" → **accepted**: AE-0304 promoted to a hard
  `Blocked by`.
- 2026-07-01 (skeptical review R3, GLM 5.2): WARN "auto-reboot can fire mid-deploy or
  mid-rotation" → **accepted**: added a lock-file/deferral requirement so auto-reboot
  never fires during a deploy or rotation, plus an AC.
- 2026-07-01 (skeptical review R4, GLM 5.2): WARN "CF analytics availability
  unverified" → **accepted**: the traffic source must be **pre-verified** (token/scope/
  retention) before adoption, else nginx logs are used and stated up front. The
  reboot/rotation lock is also honored by the AE-0300 CF-range refresh (cross-linked).
- 2026-07-01 (skeptical review R5, GLM 5.2): WARN "'all healthy' AC contradicts the
  frontend de-scope" → **accepted**: the health AC now excludes the de-scoped frontend
  (tracked separately) and only requires the reboot not to worsen its pre-existing
  state — removing the ambiguous gate.
- 2026-07-01 (skeptical review R6, GLM 5.2): WARN "shared lock has no owner/lifecycle"
  → **accepted**: this reboot-owner ticket now defines the lock's path/holder/TTL/
  watchdog/staleness/force-clear/crash-revert; AE-0300 and AE-0306 reference it rather
  than each inventing one.
- 2026-07-01 (skeptical review R7, GLM 5.2): WARN "`main`-push auto-deploy — the primary
  mutator — has no defined lock interaction" → **accepted**: the deploy must
  acquire-or-fail-closed (operator-visible) or a deploy-freeze holds `main` during
  rotation/reboot windows; added as scope + AC so the triggering path is controlled,
  not just the consumer.
- 2026-07-01 (skeptical review R8, GLM 5.2): WARN "lock is defined but never wired to
  `unattended-upgrades`" → **accepted**: specified a concrete lock→reboot bridge
  (cron+lock reboot script or apt.conf.d guard) + a test AC. WARN "auto-reboot stays off
  forever if AE-0306 slips" → **accepted**: added a slip-escalation AC (enable on close
  or logged-extension re-baseline; lapsed extension enables lock-honored auto-reboot).
- QA classification (CLAUDE.md CI/config path, AE-0153): pure ops/runtime (apt,
  reboot, unattended-upgrades config) with no in-repo behavior to `.feature`-test;
  verification is the documented post-reboot smoke + `stat`/`uname`/`docker ps`
  checks captured in the gate log. No `.feature` claimed; QA signs off.

## Implementation Plan

1. Announce/choose a maintenance window.
2. `apt-get update && apt-get upgrade -y` (then `dist-upgrade` if kernel held).
3. `reboot`; wait; verify containers healthy + site 200 through Cloudflare.
4. Set `Unattended-Upgrade::Automatic-Reboot "true";` + reboot time in
   `/etc/apt/apt.conf.d/50unattended-upgrades`.
5. Confirm `/var/run/reboot-required` gone.

## Progress Log

### 2026-07-01

Ticket created from the 2026-07-01 production security scan (finding #3, MEDIUM).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
