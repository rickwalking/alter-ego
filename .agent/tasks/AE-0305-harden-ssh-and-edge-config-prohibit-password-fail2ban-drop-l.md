# AE-0305 — harden ssh and edge config (prohibit-password, fail2ban, drop localhost from prod csp)

Status: Ready
Tier: T1
Priority: Medium
Type: Security
Area: Deployment
Owner: Unassigned
Branch: TBD
Created: 2026-07-01
Updated: 2026-07-01

## Goal

Close the remaining low-severity hardening gaps found in the 2026-07-01 scan:
tighten root SSH to key-only-by-policy, add brute-force throttling, and remove a
development artifact (`http://localhost:8000`) from the production CSP.

## Problem

The 2026-07-01 security scan surfaced three low-risk-but-cheap-to-fix items:

1. **`PermitRootLogin yes`** — password auth is already disabled
   (`PasswordAuthentication no`, one key in `authorized_keys`), so brute force is
   not currently viable, but `prohibit-password` makes the key-only policy explicit
   and future-proof against a config drift that re-enables passwords.
2. **No `fail2ban`** — `systemctl is-active fail2ban → inactive`. Low impact given
   key-only auth, but it is standard defense in depth for the SSH-exposed port.
3. **CSP dev artifact in production** — the served Content-Security-Policy contains
   `img-src 'self' data: blob: https: http://localhost:8000`. The
   `http://localhost:8000` entry is a development leftover that has no meaning in
   production and should be dropped so the prod CSP is clean. **Scope note:** this is
   dev-artifact _hygiene_, not a CSP tightening — the policy already allows any HTTPS
   image via the bare `https:` source, so removing the localhost entry does not
   materially reduce exfil surface. Tightening the `img-src https:` wildcard is a
   separate, larger decision, explicitly **out of scope** here (flagged so the residual
   is visible and can be taken on its own later).

None of these is individually urgent; bundling them as one low-priority hardening
pass keeps the noise down.

## Scope

- Set `PermitRootLogin prohibit-password` in `sshd_config` (keep key-only; do not
  disable root entirely since it is the only admin account) and reload sshd.
- Install and enable `fail2ban` with the `sshd` jail, **tailored to avoid
  self-lockout**: `ignoreip` must include the AE-0300 SSH admin-IP allow-list (the
  same source), use a conservative threshold + longer `findtime`/`bantime`, and the
  **unban procedure (`fail2ban-client unban <ip>`) must be documented in the same
  runbook as the AE-0300 SSH break-glass**. Rationale: with key-only auth already on
  and (post-AE-0300) SSH restricted to admin IPs, fail2ban is marginal
  defense-in-depth whose main _new_ risk is banning the operator's own IP — so it is
  scoped to not do that. If the admin IP is too dynamic for a safe `ignoreip`, this
  sub-item may be dropped (documented) rather than risk the only access path.
- Remove `http://localhost:8000` from the production CSP `img-src`. First `grep`
  **both** nginx and the frontend (`next.config`/middleware) for `localhost:8000`
  and `img-src` to find **every** source — the CSP may be set in more than one
  layer, and fixing only one leaves the entry live. **Declare a single authoritative
  CSP layer** (nginx **xor** Next.js) and how the other is kept verifiably silent (so
  a future edit to one layer can't re-introduce drift). If both must set headers,
  specify the env-gating mechanism — nginx headers are literals, so gating requires
  per-environment templating (`envsubst`/two configs) rather than a runtime flag; state
  which. If gating rather than removing, use an explicit env signal
  (`NODE_ENV`/`ENVIRONMENT`) so dev keeps the entry and prod does not.
- Add an **automated CSP regression guard** (a frontend headers test, or a
  Playwright browse of image-bearing routes asserting no CSP console errors) so a
  future CSP change cannot silently break images — CSP failures are browser-only and
  otherwise invisible to server-side gates.

## Non-Goals

- Not creating a separate non-root admin user / disabling root login entirely
  (larger operational change; can be a follow-up).
- Not moving the SSH port or adding 2FA.
- Not rewriting the rest of the (already strong) CSP or other security headers.

## Acceptance Criteria

- [ ] `sshd -T | grep permitrootlogin` → `permitrootlogin prohibit-password`, and
      key-based root login still works (verified before closing the session).
- [ ] `systemctl is-active fail2ban` → `active`, with the `sshd` jail enabled
      (`fail2ban-client status sshd` succeeds), the admin IP in `ignoreip`, and the
      `fail2ban-client unban` procedure documented alongside the AE-0300 SSH
      break-glass (or, if the admin IP is too dynamic, fail2ban is intentionally
      skipped with that decision documented).
- [ ] The production CSP served at `https://marinssolutions.com/` no longer
      contains `http://localhost:8000` in `img-src` (verified via `curl -I`), and
      images still load (no CSP regression in the browser console).
- [ ] Local/dev image loading is unaffected (if the localhost entry was needed in
      dev, it is gated to dev via an explicit env signal rather than removed globally).
- [ ] All CSP sources were located (nginx + frontend), a **single authoritative layer
      is declared** and the other is verifiably silent (or the templating/gating
      mechanism is specified), so the `curl -I` check is reliable across all routes.
- [ ] An automated CSP regression guard exists and passes on image-bearing routes.

## Repro Steps

1. `ssh root@<origin>`; `sshd -T | grep -E 'permitrootlogin'` → `yes`.
2. `systemctl is-active fail2ban` → `inactive`.
3. `curl -sI https://marinssolutions.com/ | grep -i content-security-policy` →
   contains `http://localhost:8000`.

## Affected Areas

- [ ] Backend
- [x] Frontend (CSP source, if set in Next.js config/middleware)
- [x] Tests (CSP assertion if there is a headers test; otherwise documented curl check)
- Deployment: `sshd_config`, `fail2ban` install/config; nginx CSP if set there
- Docs: hardening notes in the deployment runbook

## Dependencies

- Blocks: none
- Blocked by: **AE-0300** (for the SSH/fail2ban work only — its `ignoreip` shares
  AE-0300's admin-IP source, which AE-0300 verifies before pinning; shipping fail2ban
  against an unverified/dynamic admin IP risks a self-lockout with an untested
  break-glass). The **CSP sub-item is independent** and may proceed in parallel — if
  scheduling requires, split the CSP work out so it is not gated on AE-0300.
- Related: AE-0301 (secret perms)

## Implementation Plan

1. Locate the CSP definition (frontend config/middleware vs nginx); remove/gate the
   `http://localhost:8000` `img-src` entry; verify images still load.
2. Set `PermitRootLogin prohibit-password`; `sshd -t` then reload; re-verify key login.
3. `apt-get install fail2ban`; enable the `sshd` jail; confirm active.
4. Verify all three via the repro commands.

## Progress Log

### 2026-07-01

Ticket created from the 2026-07-01 production security scan (findings #6 + low/hardening notes).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- 2026-07-01 (skeptical review, GLM 5.2 — `.agent/reports/AE-0300-0305.skeptical-review.md`):
  WARN "CSP change lacks a regression net and gates on undefined env detection" →
  **accepted**: added AC to locate _all_ CSP sources (nginx + frontend), an explicit
  env signal for gating, an automated CSP regression guard, and **escalated Priority
  Low → Medium** given CSP blast radius. The SSH/fail2ban parts remain low-risk; the
  ticket priority now reflects the CSP item.
- 2026-07-01 (skeptical review R2, GLM 5.2): WARN "fail2ban is near-zero-value on
  key-only + IP-restricted SSH and may ban the operator" → **accepted**: fail2ban is
  now scoped as tailored defense-in-depth — `ignoreip` the AE-0300 admin IP,
  conservative thresholds, documented `unban` next to the break-glass, and an
  explicit escape hatch to skip it if the admin IP is too dynamic. This removes the
  self-DoS risk that would compound AE-0300's SSH allow-list.
- 2026-07-01 (skeptical review R3, GLM 5.2): WARN "SSH admin-IP assumed stable"
  (shared with AE-0300) → **accepted**: the fail2ban `ignoreip` source is the
  **same admin-IP source AE-0300 verifies before pinning** (static/VPN/jump host); if
  that source is dynamic, fail2ban's `ignoreip` sub-item is dropped via the existing
  escape hatch rather than risking a lockout.
- 2026-07-01 (skeptical review R4, GLM 5.2): WARN "AE-0305 and AE-0300 share the
  admin-IP input with no hard gate" → **accepted**: added `Blocked by: AE-0300` for the
  SSH/fail2ban work (CSP sub-item stays independent/parallelizable), so fail2ban is
  never configured against an unverified admin IP.
- 2026-07-01 (skeptical review R8, GLM 5.2): WARN "multi-source CSP env-gating
  mechanism unspecified" → **accepted**: declare a single authoritative CSP layer
  (nginx xor Next.js) + keep the other verifiably silent, or specify per-env templating
  if both must set it — so drift can't silently re-expose the dev artifact.
- 2026-07-01 (skeptical review R9, GLM 5.2): INFO "dropping localhost is cosmetic given
  the `https:` wildcard" → **accepted**: framed the CSP item as dev-artifact hygiene and
  explicitly scoped the `img-src https:` tightening out (residual made visible).

## Blockers

None.
