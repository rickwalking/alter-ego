# AE-0300 — lock production origin behind cloudflare to prevent waf bypass

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

Make the production droplet reachable on 80/443 **only** through Cloudflare, so an
attacker who discovers the origin IP cannot bypass Cloudflare's WAF, DDoS
protection, and rate-limiting by hitting the droplet directly.

## Problem

`marinssolutions.com` fronts through Cloudflare (edge returns `server: cloudflare`
with a strong CSP + HSTS-preload), but the origin droplet (`206.189.180.85`) is
open to the whole internet on 80/443 and `ufw` is inactive. A direct-to-origin
request bypasses Cloudflare entirely — confirmed during the 2026-07-01 security
scan:

```
curl --resolve marinssolutions.com:443:206.189.180.85 https://marinssolutions.com/
  → HTTP/1.1 200 OK
  → Server: nginx/1.31.2   (origin nginx, not the Cloudflare edge)
```

The origin even presents the real `marinssolutions.com` certificate, so it is
trivially fingerprintable via TLS SNI / certificate-transparency logs and
Shodan/Censys scans of the DigitalOcean range. Any WAF rule, bot rule, or
rate-limit configured at Cloudflare (including the public blog API 120/min/IP
limit from AE-0297) is void against a direct-origin attacker.

## Scope

- **Primary control:** a **DigitalOcean cloud firewall** (or `ufw`) that allows
  inbound 80/443 **only** from the published Cloudflare IPv4 + IPv6 ranges
  (https://www.cloudflare.com/ips/). This L4 CF-IP allow-list is the actual privacy
  boundary.
- **SSH (22) allow-list is a SEPARATE firewall object** from the Cloudflare-range
  allow-list, with its own admin-IP source(s) and its own refresh cadence — so a
  Cloudflare-range refresh (or a bug in the CF-range script) can never touch the SSH
  rule and lock out the admin path.
- **Authenticated Origin Pulls (mTLS) — REQUIRED; it closes the intra-Cloudflare
  bypass the L4 list cannot.** Install the CF origin-pull CA, `ssl_verify_client on;` +
  `ssl_client_certificate` on 443. Rationale (corrected from an earlier round's
  "cosmetic" framing): the L4 CF-IP allow-list admits **any** traffic egressing
  Cloudflare's shared ranges — including a **Cloudflare Worker `fetch()` to the origin
  IP** or another CF tenant pointing their zone at it. Those bypass the WAF/rate-limit
  while passing the L4 firewall. mTLS is precisely what rejects them: a Worker / other
  tenant does **not** present this zone's origin-pull client certificate, so
  `ssl_verify_client on` fails the handshake. So the two controls are complementary —
  **L4 closes the raw `curl --resolve` vector; mTLS closes the intra-CF (Workers /
  other-tenant) vector.** Verify at implementation that a Worker fetch is actually
  rejected. (Fullest zone-binding is Cloudflare Tunnel `cloudflared`; a follow-up if
  desired — but mTLS here is not optional.)
- Codify the CF-range allow-list in the repo: a tracked script
  (`scripts/deploy/cloudflare_firewall.sh` or equivalent) that fetches the current
  Cloudflare ranges and applies the firewall, **run on a schedule with a
  last-refresh/staleness alert**; the SSH object is managed separately.
- **Monotonic-growth guard (preventive, not just reactive):** the apply step guards
  against **unvalidated** shrinkage — it **refuses a fetch smaller than the
  last-known-good (LKG) set** (or one that fails validation) and alerts, so a
  partial/stale/cached fetch cannot darken the origin before the staleness alert fires.
  **LKG is a versioned artifact** (a committed snapshot file), and the guard compares
  each fetch against _current_ LKG. A legitimate Cloudflare range **retirement** is
  handled by a **diff-approval that re-bases LKG**: the approved smaller set is
  committed as the new LKG snapshot, and the apply compares against that — so it does
  **not** re-add the retired range (a naive additive-only apply would drift back to the
  historical superset and silently widen the surface forever). In short: guard blocks
  _unvalidated_ shrinkage; approved shrinkage advances LKG.
- **Verify the admin-IP source BEFORE pinning the SSH allow-list** (is it a static
  IP, a VPN/jump host, residential/dynamic, and where does the GitHub Actions deploy
  runner egress from?). If the admin/deploy origin is dynamic, the SSH object must
  allow a broader-but-trusted source (VPN/jump host, or documented runner ranges)
  rather than a brittle single IP — this is a **prerequisite**, not an assumption.
  If it cannot be made safe, that is a blocker to be raised, not silently shipped.
- **Break-glass:** document the out-of-band recovery path (DigitalOcean web/recovery
  console) in the runbook, so a mis-scoped 443 **and** 22 does not mean total
  lockout. The rollback script must be exercised against a **simulated Cloudflare-
  range rotation**, not only a dry-run against current live state.
- Document the firewall (both objects), origin-pull, staleness alert, and break-glass
  in `docs/deployment/`.

## Non-Goals

- Not rotating the origin IP or moving to Cloudflare Tunnel (cloudflared) — a
  heavier redesign; can be a follow-up if IP churn is desired.
- Not changing the application, TLS ciphers, or the existing edge headers.
- Not touching the SSH port exposure policy beyond keeping 22 reachable for admin
  (SSH hardening is AE-0305).

## Acceptance Criteria

- [ ] The raw direct-to-origin vector is refused at L4:
      `curl --resolve marinssolutions.com:443:<origin-ip>` from a non-CF source no
      longer returns 200 (connection blocked/timeout).
- [ ] The **intra-Cloudflare bypass is refused at nginx via mTLS**: a request that
      egresses Cloudflare's ranges but does not carry this zone's origin-pull client
      certificate (e.g. a Cloudflare Worker `fetch()` to the origin IP) fails the
      `ssl_verify_client` handshake — verified, not assumed. (This is the vector the L4
      allow-list alone cannot close.)
- [ ] Legitimate traffic through Cloudflare (`https://marinssolutions.com/`) still
      returns 200 with the site fully functional (blog listing, dashboard, public
      blog API, WebSocket/SSE carousel streaming all verified).
- [ ] Inbound 80/443 on the droplet are restricted to the current Cloudflare
      IP ranges (verified by listing the firewall rules); the SSH (22) allow-list is
      a **separate firewall object** with its own admin-IP source, and the
      CF-range refresh path provably cannot modify the SSH rule.
- [ ] A documented out-of-band **break-glass** procedure (DO console) exists for the
      case where both 443 and 22 are mis-scoped; the rollback script has been
      exercised against a **simulated CF-range rotation**. The break-glass is
      **drilled once end-to-end before close** (login → recovery console → flush the
      firewall), and the runbook records **who holds DO access + 2FA** — "documented"
      is not "tested."
- [ ] The scheduled CF-range refresh **honors the AE-0303 reboot/rotation lock**
      (skips while held) and a post-reboot **reconciliation** step re-confirms the
      applied range equals last-known-good, so a refresh cannot race a reboot into a
      stale/ambiguous firewall state.
- [ ] The CF-range fetch runs on a schedule and emits a **staleness/last-refresh
      alert to a named ops sink** (the same sink AE-0303's post-reboot smoke uses, not
      an unspecified "alert"); the apply guards against **unvalidated** shrinkage
      (refuses+alerts on a fetch smaller than the versioned LKG snapshot), while an
      **approved range retirement re-bases LKG** (committed snapshot) so it is not
      silently re-added.
- [ ] The SSH admin-IP source is **verified before pinning** (static vs
      dynamic/VPN/jump host; deploy-runner egress confirmed); if dynamic, a
      broader-but-trusted source is used. A wrong pin must not be discoverable only
      via lockout.
- [ ] Before public 22 is restricted/closed, it is **verified that no remaining
      workflow/job — including cron/scheduled Actions — reaches the droplet over
      public 22** (AE-0307 removed the old path); the `Blocked by: AE-0307` resolves
      only post-removal, so a leftover job cannot silently break the next deploy.
- [ ] Both controls are in place and complementary: the **L4 CF-IP allow-list** closes
      the raw direct-origin vector, and **Authenticated Origin Pulls (mTLS)** closes the
      intra-CF (Workers/other-tenant) vector; `verify_origin_pull.sh` asserts the
      CF-zone/nginx origin-pull state stays in sync. Neither alone is sufficient.
- [ ] The Cloudflare-range allow-list is applied by a repo-tracked, re-runnable
      script/config (not a one-off manual rule), and the procedure is documented in
      `docs/deployment/`.
- [ ] Rollback is an **executable, idempotent script** (not a prose runbook) that
      drops the firewall and disables origin pulls in one command, and it has been
      dry-run against the live droplet before this ticket closes.
- [ ] A `scripts/deploy/verify_origin_pull.sh` post-deploy check asserts the
      Cloudflare zone origin-pull setting (via the CF API) and the nginx
      `ssl_verify_client` state are **both** on and in sync (detects drift where CF
      sends a cert nginx doesn't require, or vice versa).
- [ ] Rollout is staged with a canary that does **not** reintroduce the bypass: the
      health check is **host-local** (SSH to the droplet + `curl` against
      `localhost`/the container, never opening public 443 to a non-CF source) or is
      CF-routed. The ticket states which; it must not punch a temporary non-CF hole in
      the firewall (that is the exact bypass being removed).

## Gherkin Scenarios

```gherkin
Feature: production origin only serves Cloudflare traffic

  Scenario: direct-to-origin request is blocked
    Given the droplet firewall allows 443 only from Cloudflare ranges
    And nginx requires the Cloudflare origin-pull client certificate
    When a client connects directly to the origin IP on 443 bypassing Cloudflare
    Then the request is refused (network block or mTLS failure)
    And the application is not served

  Scenario: legitimate Cloudflare traffic is unaffected
    Given a normal browser request to https://marinssolutions.com
    When the request is proxied by Cloudflare to the origin
    Then nginx accepts the Cloudflare client certificate
    And the site responds 200 with all features working

  Scenario: admin can still reach SSH
    Given the firewall restricts inbound ports
    When the admin connects to port 22 from the admin IP
    Then SSH connects normally
```

## Delta

### ADDED

- DO cloud firewall / `ufw` rules restricting 80/443 to Cloudflare ranges.
- Cloudflare Authenticated Origin Pulls (origin-pull CA + nginx `ssl_verify_client`).
- `scripts/deploy/cloudflare_firewall.sh` (fetch + apply CF ranges) — repo-tracked.
- `docs/deployment/` runbook for firewall + origin pulls + rollback.

### MODIFIED

- `nginx/nginx.conf.ssl` — require the Cloudflare origin-pull client certificate on
  the 443 server block.

### REMOVED

- Unrestricted `0.0.0.0/0` exposure of 80/443 on the origin.

## Affected Areas

- Backend: none (network/edge only)
- Frontend: none
- Database: none
- API: public blog API rate limit (AE-0297) becomes effective once origin bypass is closed
- Tests: bypass-attempt smoke check (documented curl); no unit-test surface (infra)
- Docs: `docs/deployment/` firewall + origin-pull runbook
- Prompts/LLM: none
- Observability: none
- Deployment: `deploy.yml` / firewall script; verify deploy still succeeds behind the firewall (the GitHub Actions runner reaches the droplet over SSH 22, not 443)

## Dependencies

- Blocks: effectiveness of AE-0297 public-API rate limit against direct-origin abuse
- Blocked by: **AE-0302** (Redis auth must be deployed and verified before this
  origin lockdown, so a Redis auth failure cannot strand the backend _behind_ a
  locked-down origin with no `curl --resolve` sanity path) **and AE-0307** (a stable
  SSH ingress must exist before public 22 is pinned/closed — GitHub-hosted runner
  egress is not pinnable, so without AE-0307 this lockdown would break the auto-deploy
  or lock out the operator). Both are hard `Blocked by`, not advisory notes.
- Related: AE-0305 (SSH/edge hardening — its fail2ban `ignoreip` must include this
  ticket's SSH admin-IP so the two do not compound into a lockout), AE-0301 (secret perms)

## Implementation Plan

1. Enumerate current Cloudflare IPv4/IPv6 ranges from the published endpoint.
2. Create the DO cloud firewall (or enable `ufw`) allowing 80/443 from those
   ranges only + 22 from admin IP; apply and verify with a direct-origin curl.
3. Install the Cloudflare origin-pull CA on the droplet; add `ssl_verify_client on;`
   - `ssl_client_certificate` to the 443 nginx block; enable Authenticated Origin
     Pulls in the Cloudflare dashboard/API for the zone.
4. Verify: edge traffic 200 + full-feature smoke; direct-origin refused.
5. Commit the firewall script + docs; note the manual DO/Cloudflare dashboard steps
   in the runbook (they are outside the repo but must be reproducible).

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (Cloudflare range change, admin lockout rollback)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-07-01

Ticket created from the 2026-07-01 production security scan (finding #1, HIGH).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- 2026-07-01: Chose CF-range firewall **+** Authenticated Origin Pulls (defense in
  depth) over IP-only or mTLS-only, because CF ranges are shared across all
  Cloudflare customers (an IP allow-list alone still lets any other Cloudflare zone
  reach the origin) and a firewall alone does not authenticate the peer.
- 2026-07-01 (skeptical review, GLM 5.2 — `.agent/reports/AE-0300-0305.skeptical-review.md`):
  - WARN "ordering catch-22" → **accepted**: added executable/idempotent rollback +
    canary AC, and a sequencing note requiring AE-0302 before/with this ticket.
  - INFO "mTLS rollback not codified" → **accepted**: added
    `scripts/deploy/verify_origin_pull.sh` AC coupling CF-zone state to nginx
    `ssl_verify_client` and treating the zone toggle as an API call, not a manual
    step. Open question (is a CF zone API token available to scripts?) is carried to
    the developer; if no token, the assertion degrades to a documented manual check
    and that limitation must be stated in the runbook.
- 2026-07-01 (skeptical review R2, GLM 5.2):
  - BLOCKER "lockout with weak rollback / no break-glass" → **accepted**: SSH
    allow-list is now a separate firewall object with its own cadence; added DO-console
    break-glass AC and rollback-against-simulated-rotation AC.
  - WARN "mTLS shares public CF CA, not an independent boundary" → **accepted**:
    reframed L4 CF-IP as the primary control and mTLS as explicit defense-in-depth;
    added scheduled CF-range refresh + staleness alert.
  - INFO "AE-0302 sequencing not machine-enforced" → **accepted**: promoted to a hard
    `Blocked by: AE-0302` field (mirrored by `Blocks: AE-0300` on AE-0302).
  - Missing-evidence "how is Dev Complete gated for untestable infra?" → **QA
    classification (per CLAUDE.md CI/config path, AE-0153):** this is infra/deployment
    with no in-repo public behavior to `.feature`-test; the tracked repo artifacts
    (`cloudflare_firewall.sh`, `verify_origin_pull.sh`, nginx `.ssl` config) get unit/
    shellcheck coverage where possible, and the network assertions
    (`curl --resolve` direct-origin refused; edge 200) are documented, reproducible
    commands captured in the gate log. No `.feature` claimed; QA signs off on that
    classification.
- 2026-07-01 (skeptical review R3, GLM 5.2): WARN "CF-range refresh can silently
  strand the origin" → **accepted**: added an additive **monotonic-growth guard**
  (refuse a shrinking/invalid fetch, alert) — preventive, not just the reactive
  staleness alert. WARN "SSH admin-IP assumed stable" → **accepted**: verifying the
  admin/deploy-runner IP source is now a prerequisite AC, with a broader-trusted
  source (VPN/jump host) required if dynamic.
- 2026-07-01 (skeptical review R4, GLM 5.2): WARN "canary contradicts the L4 boundary"
  → **accepted**: canary redefined as host-local (or CF-routed), never a temporary
  non-CF firewall hole. WARN "CF-range refresh not coordinated with the reboot lock" →
  **accepted**: refresh honors the AE-0303 lock + post-reboot reconciliation. INFO
  "break-glass documented not tested" → **accepted**: added a one-time break-glass
  drill AC + record DO access/2FA holders. The admin-IP source remains a hard
  prerequisite the developer must resolve against real deploy/login origins before
  pinning (flagged as blocker-if-unresolvable, not shipped on assumption).
- 2026-07-01 (skeptical review R5, GLM 5.2): BLOCKER "SSH allow-list not pinnable for
  GitHub-hosted runners → breaks auto-deploy or is cosmetic" → **accepted**: spun out
  **AE-0307** (stable SSH ingress: jump host / self-hosted runner / Tailscale) and made
  this ticket `Blocked by: AE-0307`. WARN "AOP is near-zero value / overstated" →
  **accepted**: demoted mTLS to an explicit optional audit-checkbox; L4 CF-IP list is
  the sole real control; noted Cloudflare Tunnel as the real zone-binding follow-up.
- 2026-07-01 (skeptical review R7, GLM 5.2): WARN "monotonic guard re-adds an
  approved-removed range" → **accepted**: LKG is a versioned snapshot re-based on
  approved removals (the guard blocks only _unvalidated_ shrinkage). WARN
  "main-push deploy has no lock interaction" → **accepted** (resolved in AE-0303, the
  lock owner) + AC here to verify no job reaches public 22 before closing it.
- 2026-07-01 (skeptical review R8, GLM 5.2): missing-evidence "staleness alert sink
  unnamed" → **accepted**: the CF-range staleness alert routes to the named ops sink
  shared with AE-0303's post-reboot smoke.
- 2026-07-01 (skeptical review R9, GLM 5.2): WARN "L4 admits Cloudflare Workers, so the
  bypass isn't fully closed — and mTLS actually _does_ reject Workers, contradicting the
  earlier 'cosmetic' framing" → **accepted, corrected an over-correction**: mTLS is
  **re-promoted to a required, complementary control** — L4 closes the raw vector, mTLS
  closes the intra-CF (Workers/other-tenant) vector. AC #1 was split so it no longer
  overstates "refused" for the intra-CF path. (Supersedes the R5 "cosmetic" demotion.)

## Blockers

None.

## Final Summary

Pending.
