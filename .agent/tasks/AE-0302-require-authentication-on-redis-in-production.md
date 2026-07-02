# AE-0302 — require authentication on redis in production

Status: In Development
Tier: T2
Priority: Medium
Type: Security
Area: Backend
Owner: Claude (developer-skill)
Agent Lane: architect → developer → qa → release
Branch: feat/ae-0300-0307-prod-security
Kanban Card: TBD
Created: 2026-07-01
Updated: 2026-07-01

## Goal

Require a password on the production Redis instance and authenticate every backend
Redis connection, removing unauthenticated read/write access to workflow state for
anything else on the Docker network.

## Problem

The 2026-07-01 security scan found Redis running with **no authentication**:

```
docker exec alter-ego-redis-1 redis-cli CONFIG GET requirepass   → (empty)
docker exec alter-ego-redis-1 redis-cli PING                      → PONG
```

Redis is not published to the host (only reachable on the internal
`alter-ego` Docker network), so it is not directly internet-exposed. But with
Docker's default `icc=true`, **any** container on that network — including the
stale `*-test` containers (AE-0304) and any future compromised service — has
unauthenticated read/write to Redis, which holds carousel checkpoints, workflow
state, and the Redis Streams event log (workflow audit/eventing). That is an
unnecessary lateral-movement and data-integrity risk; auth is cheap defense in
depth.

## Scope

- Set `requirepass` on the Redis container in `docker-compose.prod.yml`, with
  `REDIS_PASSWORD` sourced from GitHub Secrets → deploy `.env` (per the
  `do-droplet-prod-deploy` deploy model).
- **Server-side fail-closed (symmetric with the backend):** an empty/absent
  `REDIS_PASSWORD` must make the **Redis container refuse to start** in prod, NOT
  start with `requirepass ""` (which is silent no-auth). Naively passing
  `redis-server --requirepass ${REDIS_PASSWORD}` with an empty var yields an OPEN
  Redis while the backend fails closed — i.e. the exact hole this ticket closes, with
  the app down so nobody notices. Use an entrypoint/wrapper (or config-render step)
  that exits non-zero when `ENVIRONMENT` is production/unset and `REDIS_PASSWORD` is
  empty. The two fail-closed halves (backend + container) are both required.
- Wire the password through a **single Redis client factory** — one function that is
  the only sanctioned way to build a Redis client; there is no direct
  `redis.Redis(...)` / `Redis.from_url(...)` construction outside it. Audit and route
  every existing consumer (Streams publisher/consumer, cache, checkpoint, healthcheck)
  through it. **Preserve per-consumer connection semantics:** the factory's parameter
  surface must cover `db` index, `decode_responses`, pool size, and socket/blocking
  timeouts, because a blocking `XREAD` (Streams) and a cache have different needs —
  audit each consumer's pre-factory params and assert **no param loss** (a Streams
  consumer must not be starved by a shared cache pool, or silently repointed to db 0).
- **Enforce the factory with a rule-fires lint/test** (per CLAUDE.md AE-0180): a
  checker that greps for direct `redis.Redis(`/`Redis.from_url(`/`from redis import`
  outside the factory module and FIRES (non-zero exit) on a seeded violation — so a
  future consumer cannot silently bypass the authed path. An audit alone is not
  enforcement.
- Define precedence vs any existing `REDIS_URL`/`redis://` string, and treat a URL
  whose credentials are **absent or empty** (`redis://:@host`, `redis://host`, or a
  `?password=`-less variant) as _missing credentials_ in production. **Conflict rule:**
  if both `REDIS_URL` (with embedded creds) and `REDIS_PASSWORD` are set and they
  disagree, **fail closed** with a clear `ConfigError` in prod rather than silently
  picking one — a stale `REDIS_URL` must not be able to override the managed password.
- **Fail closed on the environment gate:** the prod-requires-auth check must trigger
  when `ENVIRONMENT` is `production` **or unset/unrecognized** — an unset/misspelled
  `ENVIRONMENT` must NOT silently drop to the dev "unauth OK" path (that would fail
  in the dangerous direction). Only an _explicit_ dev/test/local value relaxes it.
- Add the secret to `.env.example` (placeholder) and document it.
- Ensure healthchecks (`redis-cli ping`) still work with auth (use `-a` / `REDISCLI_AUTH`).
- **Enumerate EVERY container/process on `alter-ego-redis-1`, not just backend code.**
  Verified 2026-07-01: **Langfuse and langfuse-worker also use this Redis**
  (`REDIS_CONNECTION_STRING=redis://redis:6379`, currently unauthenticated) alongside
  the backend. Enabling `requirepass` will **NOAUTH Langfuse** (observability outage)
  unless its `REDIS_CONNECTION_STRING` is updated to carry the password
  (`redis://:${REDIS_PASSWORD}@redis:6379`) via GitHub Secrets. This wiring is
  **outside the backend factory's reach** (third-party container config) and must be an
  explicit deliverable. The factory-lint's guarantee is therefore "no **backend** code
  bypasses auth," not "all consumers are authed" — the third-party consumers are
  covered by config, not the lint.
- **Lock down runtime admin commands so auth cannot be silently disabled from inside.**
  An authenticated but compromised peer could `CONFIG SET requirepass ""` to re-open
  Redis for the whole network, invisibly regressing this ticket. In the prod Redis
  config, `rename-command` (disable) the dangerous admin verbs the app does not need —
  `CONFIG`, `FLUSHALL`, `FLUSHDB` (and consider `DEBUG`, `SHUTDOWN`) — leaving only the
  data-plane ops (GET/SET/XADD/XREAD/etc.). **Validate the rename set against
  langfuse-worker's needs first** — it uses BullMQ (ioredis), which historically issues
  `CONFIG GET maxmemory-policy` and similar; a blanket `rename-command CONFIG ""` can
  break the queue. Either scope the renames so shared consumers still work, or **split
  Redis into a backend-only instance + a Langfuse-only instance** so the lockdown does
  not have to accommodate a third party. Verify this with two **separate,
  non-contradictory** checks (since disabling `CONFIG` makes `CONFIG GET requirepass`
  itself unavailable): (a) a **build-time** assertion that the `rename-command` lines
  are present in the rendered prod Redis config (this is the config-integrity guarantee
  that auth can't be re-opened via `CONFIG SET requirepass ""`); (b) a **runtime**
  probe that an unauthenticated command returns `NOAUTH` (auth is required now). Do not
  claim the runtime probe proves "cannot be re-opened" — that is the build-time check's
  job.

## Non-Goals

- Not enabling Redis TLS (in-cluster traffic on a private Docker network; TLS is a
  larger change — track separately if desired).
- Not restricting Docker inter-container connectivity (`icc=false`) — that is a
  broader network-segmentation change beyond this ticket.
- Not changing what data is stored in Redis.

## Acceptance Criteria

- [ ] `docker exec alter-ego-redis-1 redis-cli PING` **fails** with NOAUTH, and
      `redis-cli -a <password> PING` returns `PONG`.
- [x] **Empty/absent `REDIS_PASSWORD` in prod ⇒ the Redis container refuses to start
      (unhealthy/exit), NOT an open `requirepass ""` instance.** The empty-secret
      branch is tested in the prod gate, not only the happy path — so the most likely
      deploy failure cannot silently reopen Redis. (Entrypoint seeded-violation tests
      + real-Docker verification: empty password in production ⇒ exit 1.)
- [x] The factory preserves each consumer's `db`/`decode_responses`/pool/timeout
      settings (unit test asserts no param loss), not just that all clients use it.
- [ ] Dangerous admin commands (`CONFIG`, `FLUSHALL`, `FLUSHDB`, …) are disabled via
      `rename-command` in prod, verified by **two non-contradictory checks**: (a)
      build-time assertion that the `rename-command` lines are present in the rendered
      config (integrity: auth cannot be re-opened via `CONFIG SET requirepass ""`); and
      (b) runtime probe that an unauthed command returns `NOAUTH` (auth required now).
      (The earlier `CONFIG GET requirepass` non-empty check is **removed** — it is
      self-contradictory once `CONFIG` is disabled; auth presence is proven by the
      NOAUTH probe, integrity by the build-time config assertion.)
- [ ] The backend connects successfully with the credential (carousel generation,
      checkpoint resume, and Redis Streams eventing all work end-to-end).
- [ ] **Every** container on `alter-ego-redis-1` is authed post-change — including
      **Langfuse + langfuse-worker** (their `REDIS_CONNECTION_STRING` carries the
      password); Langfuse traces/queue keep working (verified), and the `rename-command`
      set does not break langfuse-worker's BullMQ (or Redis is split per-consumer).
- [x] `REDIS_PASSWORD` is sourced from GitHub Secrets and written into the deploy
      `.env`; `.env.example` documents the placeholder. (Secret set 2026-07-02; the
      deploy's never-blank loop rejects a blank value BEFORE taking the stack down.)
- [ ] The Redis container healthcheck passes with auth enabled.
- [x] Fail-fast is **environment-gated and fails closed**: with `ENVIRONMENT`
      `production` _or unset/unrecognized_ and no credential, the backend raises a
      clear `ConfigError` at startup; only an explicit dev/test/local value allows an
      absent password (so local/CI still run). (`validate_redis_credentials` in
      `run_startup_validations`, delegating to the factory's policy; unit-tested.)
- [x] All Redis clients are built via the single factory; a **rule-fires test**
      proves the checker FIRES on a seeded direct-`redis.Redis(` usage outside the
      factory (non-zero exit / severity), not merely that the current tree is clean.
      (`scripts/check_redis_factory.py`, wired as the `backend:redis-factory` gate in
      `gates.sh`; import-based detection so any construction path is caught.)
- [x] Unit tests cover: authenticated URL construction, **absent/empty credentials
      treated as missing in prod**, the fail-closed env gate (unset `ENVIRONMENT` ⇒
      requires auth), and the explicit dev/test unauth-allowed path — mocking Redis.
      (30 new tests across factory / checker / entrypoint / startup-guard files.)

## Gherkin Scenarios

```gherkin
Feature: redis requires authentication in production

  Scenario: unauthenticated access is rejected
    Given Redis is configured with requirepass in production
    When a client issues a command without authenticating
    Then Redis returns a NOAUTH error

  Scenario: missing password fails closed on the server side too
    Given ENVIRONMENT is production and REDIS_PASSWORD is empty or unset
    When the Redis container starts
    Then it refuses to start (exits non-zero / unhealthy)
    And it does NOT run as an open, unauthenticated instance

  Scenario: the backend authenticates successfully
    Given the backend is configured with the Redis password from the environment
    When it publishes a workflow event to Redis Streams
    Then the command succeeds and the event is recorded

  Scenario: missing credential fails fast
    Given the Redis password env var is unset
    When the backend builds its Redis client
    Then it raises a clear configuration error rather than connecting unauthenticated
```

## Delta

### ADDED

- `REDIS_PASSWORD` secret (GitHub Secrets → deploy `.env`), `.env.example` placeholder.
- `requirepass` on the Redis service; authenticated backend client construction.

### MODIFIED

- `docker-compose.prod.yml` — Redis `command`/config + healthcheck with auth.
- Backend Redis client/URL construction (Streams eventing + cache/checkpoint clients).

### REMOVED

- Unauthenticated Redis access on the internal Docker network.

## Affected Areas

- Backend: Redis Streams eventing, cache/checkpoint client construction, settings
- Frontend: none
- Database: none (Redis only)
- API: none directly (workflow eventing behind it)
- Tests: authenticated-client construction unit tests; integration resume/eventing
- Docs: `.env.example` + deployment runbook
- Prompts/LLM: none
- Observability: workflow event stream must keep flowing (verify Langfuse/trace unaffected)
- Deployment: new secret must exist in GitHub Secrets before deploy, else Redis/back­end fail to start

## Dependencies

- Blocks: **AE-0300** (origin lockdown must not land until Redis auth is deployed and
  verified — a hard cross-ticket gate, mirrored by `Blocked by: AE-0302` on AE-0300)
- Blocked by: **AE-0301** (this ticket writes a **new** live secret, `REDIS_PASSWORD`,
  to the deploy `.env`; without AE-0301's `umask 077` fix landing first, that secret is
  written world-readable — re-creating the exact 644 exposure being fixed). Any
  secret-adding ticket inherits this gate.
- Related: AE-0304 (stale containers on the same network amplify the current risk; the
  `CONFIG`-lockdown above closes the lateral re-open path from a compromised peer)

## Implementation Plan

1. Add `REDIS_PASSWORD` to GitHub Secrets and `.env.example`.
2. Set `--requirepass` on the Redis service + fix healthcheck to authenticate.
3. Update backend Redis client construction to include the credential; fail fast if
   missing in production.
4. Test locally (auth on), run carousel E2E + eventing; deploy and verify NOAUTH
   for unauthenticated `redis-cli`.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (missing credential, healthcheck, reconnect)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-07-01

Ticket created from the 2026-07-01 production security scan (finding #4, MEDIUM).

### 2026-07-02 — In Development (developer-skill)

- Spec first: `backend/tests/features/redis_auth.feature` (8 scenarios incl. both
  fail-closed halves, env-gate, conflict rule, checker rule-fires).
- **Backend factory**: new `infrastructure/redis_clients/` package —
  `create_redis_client` is the only sanctioned construction site;
  `resolve_authed_redis_url` implements the credential policy (empty URL fragment =
  missing; URL-vs-managed conflict ⇒ `RedisConfigError`; production-like incl.
  unset/unrecognized env ⇒ credential required). `RedisStreamEventPublisher` routed
  through it (decode_responses preserved). Startup guard
  `validate_redis_credentials` added to `run_startup_validations`.
- **Enforcement**: `scripts/check_redis_factory.py` + `backend:redis-factory` gate in
  `gates.sh`; rule-fires tests (seeded `from redis.asyncio import` / `import redis`
  fire; factory path allowed; first-party `redis_clients` import not flagged).
- **Server-side fail-closed**: `scripts/deploy/redis-entrypoint.sh` (mounted in
  `docker-compose.prod.yml`) — refuses to start on empty `REDIS_PASSWORD` in a
  production-like env; sets `requirepass` + `rename-command` lockdown
  (CONFIG/FLUSHALL/FLUSHDB/DEBUG/SHUTDOWN). Verified against real Redis in local
  Docker: unauth PING ⇒ NOAUTH; authed PING ⇒ PONG; `CONFIG` ⇒ unknown command;
  healthcheck cmd green; empty password ⇒ exit 1.
- **Compose**: authed healthcheck (`REDISCLI_AUTH`); backend gets `REDIS_PASSWORD`
  (URL stays credential-free so the sources cannot conflict); **Langfuse +
  langfuse-worker `REDIS_CONNECTION_STRING` now carry the password** (the R9
  shared-Redis catch); all redis `depends_on` upgraded to `service_healthy`.
- **Deploy**: `REDIS_PASSWORD` written from GitHub Secrets (secret set 2026-07-02),
  added to the never-blank fail-fast loop; post-deploy runtime probe fails the
  deploy if unauth PING returns PONG or authed PING fails.
- Deploy-time ACs (NOAUTH on prod, backend E2E, Langfuse verified, healthcheck in
  prod) remain open until the first deploy of this branch.

## Files Touched

- `backend/src/rag_backend/infrastructure/redis_clients/{__init__,factory,constants}.py` — new
- `backend/src/rag_backend/infrastructure/events/redis_stream_publisher.py` — via factory
- `backend/src/rag_backend/infrastructure/events/factory.py` — no-arg publisher
- `backend/src/rag_backend/infrastructure/config/settings.py` — `redis_password`
- `backend/src/rag_backend/bootstrap/startup_validation.py` — `validate_redis_credentials`
- `scripts/check_redis_factory.py` — new checker; `scripts/ci/gates.sh` — `backend:redis-factory` gate
- `scripts/deploy/redis-entrypoint.sh` — new fail-closed entrypoint
- `docker-compose.prod.yml` — redis entrypoint/healthcheck/env; backend + Langfuse×2 auth; `service_healthy`
- `.github/workflows/deploy.yml` — secret wiring + never-blank + runtime NOAUTH probe
- `.env.example`, `docs/deployment/DEPLOYMENT_GUIDE.md` — documentation
- `backend/tests/features/redis_auth.feature` — new
- `backend/tests/unit/infrastructure/test_redis_client_factory.py` — new (14)
- `backend/tests/unit/scripts_ci/test_check_redis_factory.py` — new (5)
- `backend/tests/unit/scripts_ci/test_redis_entrypoint.py` — new (6)
- `backend/tests/unit/bootstrap/test_startup_validation_redis.py` — new (5)

## Test Evidence

```
backend$ uv run pytest tests/unit/infrastructure/test_redis_client_factory.py \
  tests/unit/scripts_ci/test_check_redis_factory.py \
  tests/unit/scripts_ci/test_redis_entrypoint.py \
  tests/unit/bootstrap/test_startup_validation_redis.py -q
30 passed

$ docker run ... redis:7-alpine sh redis-entrypoint.sh (ENVIRONMENT=production, REDIS_PASSWORD=testpw)
unauth ping  → NOAUTH Authentication required.
authed ping  → PONG
CONFIG GET   → ERR unknown command 'CONFIG'
healthcheck  → HEALTHY
(ENVIRONMENT=production, REDIS_PASSWORD=) → FATAL ... Refusing to start; exit=1
```

## QA Report

Pending.

## Decision Log

- 2026-07-01: Scoped to auth only (not TLS / not `icc=false`) — auth removes the
  unauthenticated-access risk at low cost; network segmentation is a larger,
  separate effort.
- 2026-07-01 (skeptical review, GLM 5.2 — `.agent/reports/AE-0300-0305.skeptical-review.md`):
  WARN "missing-credential path under-specified / asymmetrical" → **accepted**: added
  single shared construction path + construction-site audit, env-gated fail-fast
  (prod raises, dev/test unauth OK), empty-password-fragment = missing-cred, and the
  corresponding unit tests. Sequencing note: this ticket lands **before/with AE-0300**
  so a Redis auth failure is diagnosable before the origin is locked down.
- 2026-07-01 (skeptical review R2, GLM 5.2): WARN "shared path asserted not proven /
  empty-fragment bypassable / env gate wrong-direction" → **accepted**: shared path is
  now a single **factory enforced by a rule-fires lint test**, credential-absence
  detection covers empty + `?password=`-less variants, and the env gate **fails
  closed** (unset `ENVIRONMENT` ⇒ requires auth). INFO "sequencing not machine-
  enforced" → **accepted**: promoted to a hard `Blocks: AE-0300`.
- 2026-07-01 (skeptical review R4, GLM 5.2): BLOCKER "fail-closed only on the backend;
  empty `REDIS_PASSWORD` ⇒ open Redis + down app" → **accepted**: added a symmetric
  **server-side fail-closed** (container refuses to start on empty password in prod)
  - an AC + a Gherkin failure scenario testing the empty-secret branch. WARN "factory
    may flatten connection semantics" → **accepted**: factory param surface
    (db/decode_responses/pool/timeouts) specified with a no-param-loss unit test.
- 2026-07-01 (skeptical review R5, GLM 5.2): WARN "new `REDIS_PASSWORD` written 644
  until AE-0301" → **accepted**: added `Blocked by: AE-0301`. WARN "`CONFIG SET
requirepass ''` runtime regression" → **accepted**: disable dangerous admin commands
  via `rename-command` + a post-deploy probe that auth stays required at runtime.
- 2026-07-01 (skeptical review R6, GLM 5.2): WARN "the CONFIG-disabled state makes the
  `CONFIG GET requirepass` probe self-contradictory" → **accepted**: split into a
  build-time config-integrity assertion (rename-command lines present) + a runtime
  NOAUTH probe; dropped the contradictory runtime "cannot be re-opened" claim.
- 2026-07-01 (skeptical review R7, GLM 5.2): WARN "a leftover standalone `CONFIG GET
requirepass` non-empty AC still contradicts `rename-command CONFIG`" → **accepted**:
  **removed** that AC entirely (auth presence = NOAUTH probe; integrity = build-time
  config assertion), so no two ACs are mutually exclusive at QA time.
- 2026-07-01 (skeptical review R9, GLM 5.2): WARN "Redis is shared with Langfuse; the
  backend factory can't cover a third-party container" → **accepted and verified on the
  box**: Langfuse + langfuse-worker use `redis://redis:6379`. Added scope + AC to auth
  every consumer (Langfuse `REDIS_CONNECTION_STRING` gets the password via Secrets),
  validate the `rename-command` set against langfuse-worker's BullMQ (or split Redis),
  and restated the lint scope as "no _backend_ code bypasses auth." This is the highest-
  value catch of the review — it would otherwise be a post-deploy Langfuse outage.

## Decision Log (implementation)

- 2026-07-02: **Shared Redis kept (no split)** — the `rename-command CONFIG ""`
  lockdown was validated against the shared consumer: langfuse-worker:3.185 runs
  **BullMQ 5.76.3** (checked in the running container), and BullMQ 5.x tolerates an
  unavailable `CONFIG` (standard on ElastiCache/MemoryDB deployments). Langfuse
  worker health is explicitly re-verified at rollout (deploy-time AC); if it
  regresses, the fallback recorded here is splitting Redis per consumer.
- 2026-07-02: Factory enforcement is **import-based** (`\bredis\b` word boundary)
  rather than call-pattern-based — you cannot construct a client without the import,
  so `Redis(...)`, `Redis.from_url`, and `ConnectionPool` bypasses are all caught,
  with zero false positives on the first-party `redis_clients` package.

## Blockers

None.

## Final Summary

Pending.
