# AE-0307 — provide a stable ssh ingress path for prod deploys (jump host or self-hosted runner)

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

Establish a **stable, restrictable source** for SSH (22) access to the production
droplet — a jump host, a self-hosted GitHub Actions runner, or a VPN/Tailscale
egress — so that AE-0300 can lock port 22 to a small known set without breaking the
`main`-push auto-deploy or locking out the operator.

## Problem

AE-0300 wants to restrict inbound 22 to "admin IP(s)". But two facts make a naive
IP pin unsafe:

- **The auto-deploy runs from GitHub-hosted Actions runners** (per CLAUDE.md, every
  push to `main` deploys over SSH 22). GitHub-hosted runners egress from a **large,
  rotating pool of CIDRs**, not a stable set. Pinning 22 to that pool is either
  effectively open (defeats the hardening) or pinned to IPs that rotate and
  **silently break deploys** → production drift, an unreconciled Alembic head, or
  stale security patches.
- **The operator IP may be dynamic** (ISP/travel), so a single admin-IP pin risks
  self-lockout with only the DO-console break-glass.

The real fix is infrastructure that AE-0300 assumes but does not build: a fixed
ingress. Options: (a) a small **jump/bastion host** with a static IP that both the
deploy and the operator SSH through; (b) a **self-hosted GitHub Actions runner** on
a static IP (or on the droplet's private network); (c) **Tailscale/WireGuard** so 22
is only reachable over the tailnet and the public 22 rule can be dropped entirely.

## Scope

- Decide among jump host / self-hosted runner / Tailscale (recommend Tailscale or an
  **off-box** self-hosted runner for least public surface) and stand it up.
  **A self-hosted runner _on the droplet itself_ is discouraged** — it collapses the
  deploy trust boundary into the production trust boundary (a compromised runner is
  already _on_ the target, and AE-0300 would "pin 22 to the droplet's own IP"), making
  AE-0307's own "ingress is a separately-hardened privileged asset" guarantee vacuous.
  If an on-box runner is chosen for cost reasons, it MUST use `localhost`/private-
  network SSH so public 22 need not be open at all — state which posture is used.
- Repoint `deploy.yml` to reach the droplet through the chosen path (tailnet address,
  bastion `ProxyJump`, or self-hosted runner) instead of the droplet's public 22 from
  a GitHub-hosted runner.
- Produce the **stable source** (static IP / tailnet CIDR) that AE-0300 pins 22 to,
  and that AE-0305 uses for fail2ban `ignoreip`.
- Document the operator's SSH path through the same channel.
- **Harden the ingress as a privileged asset (it becomes THE deploy + root-SSH trust
  boundary):** enumerate its trust material (self-hosted-runner GitHub token with
  deploy scope / bastion root SSH key / tailnet auth key), give each a **rotation
  cadence + revocation procedure**, add basic monitoring/alerting on the node, and
  define **compromise handling** ("if the ingress is popped, the attacker reaches
  origin _legitimately_ through AE-0300's allow-list" — so this node must be at least
  as hardened as the droplet: minimal packages, no extra listeners, key-only). Define
  the "ingress down / rebuild" recovery and how it interacts with the AE-0303 lock and
  AE-0301 umask on rebuild.
- **Address the ingress control-plane as a deploy SPOF:** the recommended Tailscale
  (or any coordinated) path makes deploys depend on an external control plane — a
  Tailscale outage, auth-key expiry, or ACL change blocks _all_ deploys, and the DO
  console break-glass is an admin path, **not** a deploy path. Define a deploy-DR:
  either (i) keep a second independent deploy path (DO console + a documented manual
  `docker compose pull && up` runbook), or (ii) document and drill the Tailscale-outage
  deploy procedure explicitly. State which.
- **Retire the old public-22 deploy path, don't just supersede it:** the public-22
  `deploy.yml` SSH step must be **removed/guarded**, and there must be no remaining
  workflow/job — including **cron/scheduled** Actions, not only `main`-push — that
  egresses to the droplet's public 22. Proving one deploy works over the new path is
  not enough; the old path must be gone before AE-0300 closes 22.

## Non-Goals

- Not the firewall pinning itself (that is AE-0300, which consumes this ticket's
  output).
- Not migrating the whole deploy to a different CI system.
- Not building HA for the jump host (single stable ingress is enough for now).

## Acceptance Criteria

- [ ] A stable SSH ingress exists (jump host static IP, self-hosted runner, or
      Tailscale tailnet) and its source range is documented for AE-0300 to pin.
- [ ] `deploy.yml` deploys successfully over the new path (a real deploy completes
      end-to-end), and no longer depends on the droplet's public 22 being open to
      GitHub-hosted runner ranges.
- [ ] The operator can SSH via the same stable path.
- [ ] With the stable path in place, restricting public 22 to that source (or
      dropping public 22 entirely, for Tailscale) does **not** break deploys — proven
      by a deploy after the restriction.
- [ ] The old public-22 deploy code path is **removed/guarded** (not merely
      superseded), and it is verified that **no remaining workflow/job — including
      cron/scheduled Actions — reaches the droplet over public 22**.
- [ ] The ingress's own trust material is enumerated with a rotation + revocation
      procedure, the node is hardened (key-only, minimal surface) and monitored, and a
      compromise/"ingress down" recovery is documented — it is treated as a privileged
      asset, not plumbing.
- [ ] A **deploy-DR path** is defined and drilled for a control-plane outage (e.g.
      Tailscale down): either a second independent deploy path or a documented manual
      `docker compose pull && up` runbook — the DO-console break-glass alone is not a
      deploy path.
- [ ] Rollback documented (how to re-open a temporary admin path if the ingress
      fails), coordinated with the AE-0300 break-glass.

## Gherkin Scenarios

```gherkin
Feature: deploys and admin access survive locking down public SSH

  Scenario: auto-deploy works through the stable ingress
    Given deploy.yml reaches the droplet via the jump host / self-hosted runner / tailnet
    When a change is pushed to main
    Then the deploy completes over the stable path without opening public 22 to GitHub ranges

  Scenario: public 22 restriction does not break deploys
    Given public 22 is restricted to the stable ingress source (or closed for Tailscale)
    When the next deploy runs
    Then it still connects and completes
```

## Delta

### ADDED

- A jump host / self-hosted runner / Tailscale ingress; its stable source range.

### MODIFIED

- `.github/workflows/deploy.yml` — connect via the stable path.

### REMOVED

- Dependency on the droplet's public 22 being reachable from GitHub-hosted runner IPs.

## Affected Areas

- Backend: none
- Frontend: none
- Database: none
- API: none
- Tests: a real deploy over the new path (documented); no unit surface (infra)
- Docs: `docs/deployment/` ingress + operator SSH path
- Prompts/LLM: none
- Observability: none
- Deployment: `deploy.yml` connection path; new infra (bastion/runner/tailnet)

## Dependencies

- Blocks: **AE-0300** (origin lockdown cannot safely pin/close public 22 until this
  stable ingress exists) and the SSH/fail2ban sub-item of **AE-0305**.
- Blocked by: none
- Related: memory `do-droplet-prod-deploy` (deploy-over-SSH model), CLAUDE.md
  main-push auto-deploy.

## Implementation Plan

1. Choose the ingress (recommend Tailscale on the droplet + a Tailscale step in the
   deploy, or a self-hosted runner on a static IP).
2. Stand it up; repoint `deploy.yml`; prove a full deploy over it.
3. Publish the stable source range for AE-0300 / AE-0305.
4. Restrict/close public 22 and prove deploys still work; document rollback.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (ingress down → rollback path)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-07-01

Spun out of the AE-0300 skeptical review R5 (GLM 5.2): pinning public 22 to
GitHub-hosted runner egress is not viable; a stable ingress must exist first.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- 2026-07-01: Separated from AE-0300 because "verify the admin/runner IP source" is
  not a verification but a build task — GitHub-hosted runner egress is not pinnable,
  so a stable ingress is a prerequisite deliverable, not an assumption.
- QA classification (CLAUDE.md CI/config path, AE-0153): infra/deployment; verified by
  a real deploy over the new path + the public-22-restricted deploy, documented in the
  gate log. No `.feature`-testable in-repo behavior; QA signs off.
- 2026-07-01 (skeptical review R6, GLM 5.2): BLOCKER "the ingress is a new unsecured
  SPOF" → **accepted**: added ingress trust-material enumeration, rotation/revocation,
  hardening, monitoring, and compromise/recovery handling as scope + ACs. BLOCKER "old
  public-22 path not deleted, only superseded" → **accepted**: added an AC to
  remove/guard the old path and verify no workflow (incl. cron) still uses public 22,
  which AE-0300 also checks before closing 22.
- 2026-07-01 (skeptical review R7, GLM 5.2): INFO "on-droplet runner option inverts the
  isolation model" → **accepted**: discouraged the on-box runner (recommend off-box /
  Tailscale); if on-box, it must use localhost/private-network SSH so public 22 stays
  closed — the two postures have opposite security and are no longer conflated.
- 2026-07-01 (skeptical review R8, GLM 5.2): WARN "Tailscale adds a control-plane deploy
  SPOF" → **accepted**: added a deploy-DR AC (second independent deploy path or a
  documented/drilled Tailscale-outage `docker compose` runbook) — the DO-console
  break-glass is admin-only, not a deploy path.

## Blockers

None.

## Final Summary

Pending.
