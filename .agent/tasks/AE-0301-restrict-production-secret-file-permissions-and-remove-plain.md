# AE-0301 — restrict production secret file permissions and remove plaintext env backups

Status: Ready
Tier: T1
Priority: High
Type: Security
Area: Deployment
Owner: Unassigned
Branch: TBD
Created: 2026-07-01
Updated: 2026-07-01

## Goal

Ensure production secret files are readable only by root (mode 600), remove
stale plaintext secret backups, and enforce these permissions on every deploy so
the hardening cannot silently regress.

## Problem

The 2026-07-01 security scan found the production secret files world-readable
(mode 644) on the droplet:

```
644 root root /opt/alter-ego/.env
644 root root /opt/alter-ego/backend/.env
644 root root /opt/alter-ego/.env.backup.20260602-211752
```

These hold high-value secrets: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
`PINECONE_API_KEY`, `GLM_API_KEY`, `GEMINI_API_KEY`, `POSTGRES_PASSWORD`,
`SECRET_KEY`, `ANON_SECRET_KEY`, and the full Langfuse secret set. Direct
exploitability is currently low (only root has a login shell and the files are not
bind-mounted into containers), but 644 is a severe defense-in-depth failure:
any future non-root user, a container breakout, or an app-level file-read bug
would expose the entire secret set. The plaintext `.env.backup.*` is an extra,
unnecessary copy. The deploy (`deploy.yml`) rewrites `/opt/alter-ego/.env` from
GitHub Secrets each run, so whatever created the files uses the default umask
(644) — the fix must be applied at write time in the deploy, not just once by hand.

Separately, `backend/.env` on disk carries a stale `DEBUG=true` (the running
container is `DEBUG=false` because `docker-compose.prod.yml` hardcodes it, but the
at-rest `true` is a footgun if a future compose change starts sourcing that file).

## Scope

- `chmod 600` `/opt/alter-ego/.env` and `/opt/alter-ego/backend/.env` on the
  droplet (one-time remediation).
- Remove (or `chmod 600` + relocate out of the deploy dir) the plaintext
  `/opt/alter-ego/.env.backup.*` file(s).
- Update `deploy.yml` (and/or the server-side deploy script it invokes) to set
  **`umask 077` before writing any `.env`** so the file is created `600` from the
  start (no world-readable window between create and `chmod`); keep a defensive
  `chmod 600` too.
- Add a post-deploy assertion that **fails the deploy** if any `.env` is not `600`
  (a `stat`-based check, not just a log line).
- Identify what created `/opt/alter-ego/.env.backup.*` (manual step, cron, or a
  deploy step) and either stop it or confirm it will not recur; document the finding.
- Set `DEBUG=false` at rest in `backend/.env` (compose remains the source of
  truth; this just removes the misleading/foot-gun value).
- **Estimate the exposure window** for the 644 state as a _worst-case lower bound_.
  File mtime is **invalid** here — each deploy rewrites `.env`, so mtime reflects the
  last write, not first creation; the files may have been 644 since bootstrap. Bound it
  instead by droplet creation date, first deploy in CI history, and earliest
  origin-cert sighting in CT logs / Shodan, and record it as "exposed for **at least**
  X, possibly since droplet creation." AE-0306's accept-loss decisions must be
  justified against this worst case.
- **Rotate the cheap-to-rotate keys by DEFAULT** as part of this remediation:
  `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `PINECONE_API_KEY`, `GLM_API_KEY`,
  `GEMINI_API_KEY`, and the Langfuse API/public/secret keys — regenerate in each
  provider, update GitHub Secrets, redeploy. These are billable/identity-bearing and
  rotating them has no session/DB blast radius, so "world-readable window on live
  keys" defaults to rotate, not accept.
- **Revoke-after-verify ordering, per provider:** revoke each old provider key only
  **after** a smoke confirms _that specific provider's_ new key is live and in use —
  never as an atomic part of the redeploy. A single carousel smoke typically exercises
  only OpenAI/Anthropic; GLM, Gemini, and Pinecone have distinct code paths, so the
  smoke must have a **per-provider "live and in use" assertion** or those keys can be
  revoked while mis-set, stranding the provider. "Old keys revoked" is its own verified
  step, per provider, not one blanket smoke bundled into the redeploy.
- **Where a provider has no exercisable smoke path**, the revoke gate has nothing to
  verify against. **Pre-list, per provider, the exact in-use assertion up front** (not
  discovered during execution): OpenAI/Anthropic → the carousel smoke; **GLM** (used as
  the system model, `opencode-go/glm-5.2`) → name its exerciser; **Pinecone** →
  name its exerciser (a retrieval call). For any that lack one, **pre-decide in this
  ticket (not at execution time)** which of (i) add a minimal exerciser, (ii) explicitly
  accept revoke-on-faith, or (iii) exclude — with rationale recorded, so execution
  resolves a stated choice rather than making it under deadline pressure and never
  silently revoking unverified. (Per memory `prod-no-gemini-key-by-design`, Gemini is
  excluded — not active in prod. GLM is the system model and is likely exercised by the
  carousel smoke's orchestrator step — confirm; Pinecone needs a named retrieval
  exerciser or an explicit accept/exclude decision recorded here.)

## Non-Goals

- The **expensive-to-rotate** secrets — `POSTGRES_PASSWORD`, `SECRET_KEY`,
  `ANON_SECRET_KEY`, `LANGFUSE_ENCRYPTION_KEY`/`LANGFUSE_SALT` — are **NOT** rotated
  here (DB password change needs coordinated app+DB update; `SECRET_KEY`/
  `ANON_SECRET_KEY` rotation invalidates sessions/tokens; encryption-key/salt
  rotation can strand existing encrypted Langfuse data). They move to a **tracked
  follow-up ticket, AE-0306, with a deadline** — not a free-form "decision recorded"
  line. Blocked-forward via Dependencies.
- Not migrating to a secrets manager (Vault/DO secrets) — larger change, track
  separately if desired.
- Not changing which secrets exist or how the app reads them.

## Acceptance Criteria

- [ ] `/opt/alter-ego/.env` and `/opt/alter-ego/backend/.env` are mode `600`
      owned by root on the droplet (`stat -c '%a %U' ...` → `600 root`).
- [ ] No world-readable plaintext secret backup remains in `/opt/alter-ego`
      (the `.env.backup.*` is removed or moved out with mode 600).
- [ ] The deploy sets `umask 077` before writing `.env` (files created `600`, no
      644 window), and a post-deploy `stat` check **fails the deploy** if any `.env`
      is not `600` (verified by inspecting the workflow + a fresh deploy).
- [ ] The source that created `.env.backup.*` is identified and stopped/confirmed
      non-recurring (documented in the ticket).
- [ ] The 644 exposure window is estimated and recorded.
- [ ] A **per-provider exerciser list exists as a checked artifact before execution**
      (OpenAI/Anthropic → carousel smoke; GLM → named exerciser; Pinecone → named
      retrieval exerciser; Gemini → excluded, not active in prod). This is a hard gate,
      not prose.
- [ ] The cheap-to-rotate keys are **rotated** and live via GitHub Secrets + redeploy;
      **each provider's old value is revoked only after that provider's named exerciser
      asserts its new key is in use** (per-provider revoke-after-verify — no bundled
      single smoke). A provider with no exerciser is either given a minimal one or its
      revoke-on-faith / exclusion is explicitly recorded — never revoked silently
      unverified.
- [ ] The expensive-to-rotate secrets are tracked in follow-up **AE-0306** with a
      deadline (not left as a free-form decision-log line).
- [ ] `backend/.env` on the droplet has `DEBUG=false` (or the line removed), and
      the running backend container remains `DEBUG=false`.
- [ ] The change does not break container startup (containers still read their env
      via compose `env_file`/`environment` as before).

## Repro Steps

1. `ssh root@<origin>` and run `stat -c '%a %U %G %n' /opt/alter-ego/.env /opt/alter-ego/backend/.env`.
2. Observe `644` (world-readable) on files containing API keys and DB password.
3. `ls -la /opt/alter-ego/.env.backup.*` → world-readable plaintext secret copy.

## Affected Areas

- [x] Backend (`backend/.env` at-rest DEBUG value)
- [ ] Frontend
- [x] Tests (deploy-script assertion / documented post-deploy `stat` check)
- Deployment: `.github/workflows/deploy.yml` (or its server-side script)
- Docs: note the 600 invariant in the deployment runbook

## Dependencies

- Blocks: AE-0306 (rotation of the expensive-to-rotate secrets is spun out from here)
- Blocked by: none
- Related: AE-0300 (origin lockdown), memory `do-droplet-prod-deploy` (deploy
  rewrites `.env` from GitHub Secrets — the umask/chmod must live in that same step)

## Implementation Plan

1. One-time: `chmod 600` both `.env` files; remove/relocate `.env.backup.*`.
2. Edit `deploy.yml` so the step that writes `.env` (from GitHub Secrets) appends
   `chmod 600 <file>` immediately after the write, for both root and `backend/.env`.
3. Set `DEBUG=false` in the at-rest `backend/.env` template/secret.
4. Trigger a deploy (or dry-run the write step) and confirm files land at 600.

## Progress Log

### 2026-07-01

Ticket created from the 2026-07-01 production security scan (finding #2, MEDIUM-HIGH).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- 2026-07-01 (skeptical review, GLM 5.2 — `.agent/reports/AE-0300-0305.skeptical-review.md`):
  - WARN "chmod window / cannot-regress overstated" → **accepted**: switched to
    `umask 077` at write time (no 644 window) + a deploy-failing `stat` assertion;
    dropped the absolute "cannot regress" claim.
  - WARN "`.env.backup.*` creator unidentified" → **accepted**: added AC to find and
    stop the source before closing.
  - WARN "rotation punt is weak" → **accepted**: rotation is now an explicit,
    recorded decision (see below), not a silent deferral.
- 2026-07-01 (skeptical review R2, GLM 5.2): BLOCKER "rotation deferred via a
  criteria-free AC checkbox" → **accepted and changed**. Rotation is no longer a
  free-form decision: the **cheap-to-rotate keys are rotated by default in this
  ticket** (no session/DB blast radius), and the **expensive-to-rotate secrets move
  to tracked follow-up AE-0306 with a deadline**. Split rationale: `SECRET_KEY`/
  `ANON_SECRET_KEY` rotation invalidates sessions/tokens; `POSTGRES_PASSWORD` needs a
  coordinated app+DB change; `LANGFUSE_ENCRYPTION_KEY`/`SALT` rotation can strand
  existing encrypted data — so those need their own change window, but they are now
  _tracked with a deadline_, not accepted-and-forgotten.
- 2026-07-01 (skeptical review R3, GLM 5.2): WARN "cheap-key rotation has a revoke/
  redeploy race" → **accepted**: added a **revoke-after-verify** ordering invariant
  (revoke old keys only after the post-deploy smoke confirms new keys are live).
  Coordinate the redeploy so `unattended-upgrades` auto-reboot (AE-0303) cannot fire
  mid-rotation — see AE-0303's reboot-lock resolution.
- 2026-07-01 (skeptical review R4, GLM 5.2): WARN "exposure-window mtime is invalid" →
  **accepted**: mtime is discarded (deploys rewrite `.env`); the window is a worst-case
  lower bound from droplet-creation/first-deploy/CT-log evidence, and AE-0306
  accept-loss is justified against the worst case. WARN "post-deploy smoke
  under-specified across 5 providers" → **accepted**: revoke-after-verify is now
  **per provider** with a per-provider live-in-use assertion. Note (memory
  `prod-no-gemini-key-by-design`): `GEMINI_API_KEY` is not active in prod by design, so
  it has nothing "in use" to strand — the per-provider check naturally skips inactive
  keys; only rotate/revoke keys actually provisioned in prod.
- 2026-07-01 (skeptical review R5, GLM 5.2): WARN "per-provider verify unachievable
  where no smoke path exists" → **accepted**: each provider must name its exact
  in-use assertion; where none exists, add a minimal exerciser or explicitly record
  accepting the residual (never revoke-on-faith silently).
- 2026-07-01 (skeptical review R8, GLM 5.2): WARN "per-provider exerciser is prose, not
  an enforceable AC" → **accepted**: promoted to a hard AC — the per-provider exerciser
  list must exist as a checked artifact, and each provider's revoke gates on _its own_
  exerciser, so a bundled OpenAI/Anthropic smoke can't green-light revoking GLM/Pinecone.
- 2026-07-01 (skeptical review R9, GLM 5.2): INFO "GLM/Pinecone exerciser resolution is
  deferred to execution" → **accepted**: the add-exerciser / accept-on-faith / exclude
  choice for GLM and Pinecone is pre-decided in the ticket body with rationale, not left
  to execution under deadline.

## Blockers

None.
