# AE-0301 — restrict production secret file permissions and remove plaintext env backups

Status: Dev Complete
Tier: T1
Priority: High
Type: Security
Area: Deployment
Owner: Claude (developer-skill)
Branch: feat/ae-0300-0307-prod-security
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

- [x] `/opt/alter-ego/.env` and `/opt/alter-ego/backend/.env` are mode `600`
      owned by root on the droplet (`stat -c '%a %U' ...` → `600 root`).
- [x] No world-readable plaintext secret backup remains in `/opt/alter-ego`
      (the `.env.backup.*` is removed or moved out with mode 600).
- [ ] The deploy sets `umask 077` before writing `.env` (files created `600`, no
      644 window), and a post-deploy `stat` check **fails the deploy** if any `.env`
      is not `600` (verified by inspecting the workflow + a fresh deploy).
- [x] The source that created `.env.backup.*` is identified and stopped/confirmed
      non-recurring (documented in the ticket).
- [x] The 644 exposure window is estimated and recorded.
- [x] A **per-provider exerciser list exists as a checked artifact before execution**
      (OpenAI/Anthropic → carousel smoke; GLM → named exerciser; Pinecone → named
      retrieval exerciser; Gemini → excluded, not active in prod). This is a hard gate,
      not prose.
- [ ] The cheap-to-rotate keys are **rotated** and live via GitHub Secrets + redeploy;
      **each provider's old value is revoked only after that provider's named exerciser
      asserts its new key is in use** (per-provider revoke-after-verify — no bundled
      single smoke). A provider with no exerciser is either given a minimal one or its
      revoke-on-faith / exclusion is explicitly recorded — never revoked silently
      unverified.
- [x] The expensive-to-rotate secrets are tracked in follow-up **AE-0306** with a
      deadline (not left as a free-form decision-log line).
- [x] `backend/.env` on the droplet has `DEBUG=false` (or the line removed), and
      the running backend container remains `DEBUG=false`.
- [x] The change does not break container startup (containers still read their env
      via compose `env_file`/`environment` as before — `docker compose config -q`
      parses post-chmod, stack healthy, site 200).

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

## Test-classification (AE-0153)

CI/config/tooling ticket — no public/user-visible behavior change (the deploy
workflow and a server-side assertion script change; no API, workflow, or
business rule changes). `.feature` not required; substitutes focused unit
tests **plus** the seeded-violation (rule-fires, AE-0180) tests in
`backend/tests/unit/scripts_ci/test_check_env_permissions.py` (644 file → exit
1; `.env.backup.*` present → exit 1; missing file → exit 1; wrong owner →
exit 1). Affected gate: the deploy itself (`deploy.yml` fails on violation).
QA sign-off on this classification is requested in the QA pass.

## Execution findings (2026-07-01)

- **`.env.backup.*` source identified**: no cron entry, no deploy step, and no
  repo script creates date-suffixed env backups (`git log -S`, server crontabs
  and `/etc/cron.*` checked). It was a one-time manual
  `cp` (2026-06-02 21:17). Confirmed non-recurring **and enforced**: the new
  post-deploy check fails any deploy where a `.env.backup.*` reappears.
- **644 exposure window (worst-case lower bound)**: mtime discarded (deploys
  rewrite `.env`). Bound: **at least 2026-05-04 (first `deploy.yml` run) →
  2026-07-01 (remediation), ~58 days; possibly since droplet creation
  2026-04-28 (~64 days)**. AE-0306's accept-loss decisions must be justified
  against the ~64-day worst case.
- **Per-provider exerciser pre-decisions** (details in
  `docs/deployment/ae-0301-key-rotation-runbook.md`): GLM **is** exercised by
  the carousel smoke — `LLM_PROVIDER=glm` verified in the live prod `.env`
  (not assumed); Pinecone's named exerciser is the prod RAG chat retrieval
  step (existing path — not revoke-on-faith); Anthropic is exercised by RAG
  chat, **not** the carousel smoke (prod carousel LLM is GLM); Gemini excluded
  (key empty in prod by design).

## Progress Log

### 2026-07-01

Ticket created from the 2026-07-01 production security scan (finding #2, MEDIUM-HIGH).

### 2026-07-01 — In Development (developer-skill)

- Branch `feat/ae-0300-0307-prod-security`; repo-side implementation:
  `umask 077` + defensive `chmod 600` around the `.env` write in `deploy.yml`;
  post-deploy stat assertion via new `scripts/deploy/check-env-permissions.sh`
  (fails the deploy on wrong mode/owner, missing file, or `.env.backup.*`).
- Rule-fires tests added (6, all green).
- Exerciser list + rotation runbook checked in:
  `docs/deployment/ae-0301-key-rotation-runbook.md`; 600 invariant documented
  in `DEPLOYMENT_GUIDE.md` §3.4.
- **One-time prod remediation executed and verified** over SSH: both `.env`
  files now `600 root`; `.env.backup.20260602-211752` **moved** to
  `/root/env-backups/` (dir 700, file 600 — ticket allows remove-or-relocate);
  `DEBUG=false` at rest in `backend/.env` (running container already
  `DEBUG=false`). The committed check script piped over SSH against the live
  droplet returns `ENV-PERMS OK`.
- **Not done here (by design)**: cheap-key rotation — requires provider
  dashboards (user-owned). Staged step-by-step in the runbook with
  per-provider revoke-after-verify gates.

## Files Touched

- `.github/workflows/deploy.yml` — `umask 077` before the `.env` heredoc;
  defensive `chmod 600` for both env files; post-deploy
  `check-env-permissions.sh` assertion (fails deploy under `set -e`).
- `scripts/deploy/check-env-permissions.sh` — new stat-based assertion
  (mode/owner/backup-glob), owner expectation overridable for tests.
- `backend/tests/unit/scripts_ci/test_check_env_permissions.py` — new
  rule-fires tests (seeded violations + healthy pass + usage guard).
- `docs/deployment/ae-0301-key-rotation-runbook.md` — new: 600 invariant,
  per-provider exerciser table (hard AC), rotation procedure, remediation log.
- `docs/deployment/DEPLOYMENT_GUIDE.md` — §3.4 600-invariant note + umask in
  the bootstrap snippet.
- Server-side (not in git): `/opt/alter-ego/.env` + `backend/.env` → `600
root`; backup relocated to `/root/env-backups/`; `DEBUG=false` at rest.

## Test Evidence

```
backend$ uv run pytest tests/unit/scripts_ci/test_check_env_permissions.py -q
6 passed in 0.12s

$ ssh root@206.189.180.85 'bash -s -- /opt/alter-ego /opt/alter-ego/.env \
    /opt/alter-ego/backend/.env' < scripts/deploy/check-env-permissions.sh
ENV-PERMS OK: /opt/alter-ego/.env /opt/alter-ego/backend/.env are 600 root; \
no .env.backup* in /opt/alter-ego

$ ssh root@206.189.180.85 'stat -c "%a %U %n" /opt/alter-ego/.env /opt/alter-ego/backend/.env'
600 root /opt/alter-ego/.env
600 root /opt/alter-ego/backend/.env
```

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
