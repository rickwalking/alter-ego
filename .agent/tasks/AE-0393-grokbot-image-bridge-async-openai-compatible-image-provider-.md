# AE-0393 — GrokBot image bridge: async OpenAI-compatible image provider via Grok Bot webhook

Status: In Development
Tier: T2
Priority: P1
Type: Feature
Area: backend
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: feat/ae-0393-grokbot-image-bridge
Kanban Card: TBD
Created: 2026-10-15
Updated: 2026-10-15

## Goal

Generate carousel slide images through the owner's Grok Bot (Cursor subscription, webhook-triggered,
asynchronous) instead of the paid OpenAI Images API. The bridge must be behind a flag and fall back to
OpenAI on any failure, without changing the carousel workflow.

## Problem

Every carousel pays for its images on `gpt-image-2`. The owner's existing subscriptions can generate
images: the 2026-10-15 codex spike showed usable slides in ~50 s each. The Grok Bot can receive a
webhook and call our API back. There is no provider that can wait for an asynchronous external
agent and return its result to the images phase.

## Scope

- New module `modules/image_bridge/`: job model, repository, webhook client, callback route,
  `GrokBotImageService` and `FallbackImageService`. Full design:
  `docs/architecture/grokbot-image-bridge.md`; decision: ADR-0022.
- Callback `POST /api/v1/image-bridge/jobs/{job_id}/result`. It accepts the OpenAI `ImagesResponse`
  (`b64_json`) or an OpenAI error body, authenticated with the per-job one-time token.
- Table `image_bridge_jobs` and its Alembic migration.
- Container wiring behind `IMAGE_BRIDGE_ENABLED` (code default false; prod `deploy.yml` true,
  owner decision 2026-10-15).
- Settings, `.env.example` and `deploy.yml` entries for every new setting.
- nginx `client_max_body_size 16m` on `/api/v1/image-bridge/` in both nginx configs.
- Smoke CLI `scripts/image_bridge_smoke.py`: one end-to-end job, reports seconds and dimensions.

## Non-Goals

- Configuring the Grok Bot / Cursor side; the owner does that against the contract.
- Gemini path changes; blog-post image changes beyond what the shared registry gives for free.
- A codex-on-VPS provider (possible later behind the same port).
- `url` image responses (b64 only).

## Acceptance Criteria

- [ ] AC1: With `IMAGE_BRIDGE_ENABLED=false` the container wires `OpenAIImageService` exactly as
      today (no behavior change; test proves the wiring).
- [ ] AC2: With it enabled, `generate_image` creates a pending job, POSTs the webhook payload of
      contract §2.1, waits, and writes the callback image to `output_path`. The image is
      normalized to exactly the configured size (default `1536x1024`, PNG).
- [ ] AC3: The callback accepts a valid ImagesResponse with the right token (`202`) and
      rejects:
      - a missing or wrong token, or an unknown job (`401`, same body for both);
      - a non-pending job (`409`);
      - an oversized body (`413`);
      - a malformed body or an invalid image (`422`, job marked failed).
- [ ] AC4: An OpenAI error body marks the job failed with its code and message (`202`).
- [ ] AC5: A webhook non-2xx/timeout, a failed job or an expired job raises in
      `GrokBotImageService`. `FallbackImageService` then calls OpenAI when
      `IMAGE_BRIDGE_FALLBACK_ENABLED=true`, and logs `image_provider=openai_fallback` plus the reason.
- [ ] AC6: The waiter works across processes: it polls Postgres, and the image bytes travel in
      `image_bridge_jobs.image_bytes`, which is nulled after the read.
- [ ] AC7: Tokens are stored only as SHA-256 and compared with `hmac.compare_digest`. No token,
      webhook secret or base64 appears in logs.
- [ ] AC8 (replaced by the owner decision of 2026-10-15): if the bridge is enabled but
      `GROKBOT_IMAGE_WEBHOOK_URL` or `IMAGE_BRIDGE_PUBLIC_BASE_URL` is empty, startup logs one
      ERROR (`image_bridge_misconfigured`, listing the missing setting names, never their
      values) and wires plain `OpenAIImageService`. Startup never fails (prod auto-deploys on
      merge, so a missing secret must not crash-loop prod). Both branches tested.
- [ ] AC9: Every new setting is in `settings.py`, `.env.example` and `deploy.yml`, and the
      `backend:autopilot-env`-style gate passes.
- [ ] AC10: Concurrency is capped by `IMAGE_BRIDGE_MAX_CONCURRENCY` (test with 3 concurrent
      requests and a cap of 2).
- [ ] AC11: Stale pending jobs expire after the timeout; late callbacks get `409`.
- [ ] AC12 (owner decision 2026-10-15): `deploy.yml` sets `IMAGE_BRIDGE_ENABLED=true`,
      `IMAGE_BRIDGE_FALLBACK_ENABLED=true` and `IMAGE_BRIDGE_PUBLIC_BASE_URL=https://marinssolutions.com`
      (not a secret): the bridge is the normal image path in prod and OpenAI runs only when a
      bridge job fails. `Settings` defaults stay `false`/`true`. Rollback = flag `false` in `deploy.yml`.

## Gherkin Scenarios

```gherkin
Feature: GrokBot image bridge

  Scenario: Bridge disabled keeps the OpenAI path
    Given IMAGE_BRIDGE_ENABLED is false
    When the images phase generates a slide image
    Then the OpenAI image service is called
    And no image bridge job is created

  Scenario: Grok Bot returns an image
    Given the bridge is enabled
    When the images phase requests an image
    Then a pending job is created and the Grok Bot webhook receives the prompt, size and callback token
    When the Grok Bot posts a valid OpenAI ImagesResponse with the token
    Then the callback answers 202
    And the slide image is written at the requested size

  Scenario: Wrong token
    Given a pending bridge job
    When a callback arrives with a wrong token
    Then it answers 401 and the job stays pending

  Scenario: Unknown job looks the same as a wrong token
    When a callback arrives for a job id that does not exist
    Then it answers 401 with the same body as a wrong token

  Scenario: Duplicate callback
    Given a job that already succeeded
    When the same callback arrives again
    Then it answers 409 and nothing is written

  Scenario: Grok Bot refuses
    Given a pending bridge job
    When the Grok Bot posts an OpenAI error body
    Then the job is failed with the error code
    And the OpenAI fallback generates the image

  Scenario: Grok Bot never answers
    Given a pending bridge job
    When the bridge timeout passes
    Then the job is expired and the OpenAI fallback generates the image
    And a late callback answers 409

  Scenario: Webhook is down
    When the webhook answers 500
    Then the job fails at once and the OpenAI fallback runs without waiting

  Scenario: Invalid image
    When the callback carries base64 that is not an image
    Then it answers 422 and the job is failed

  Scenario: Enabled without the bridge URLs falls back to OpenAI
    Given IMAGE_BRIDGE_ENABLED is true
    And GROKBOT_IMAGE_WEBHOOK_URL or IMAGE_BRIDGE_PUBLIC_BASE_URL is empty
    When the application starts
    Then startup logs one image_bridge_misconfigured ERROR naming the missing settings
    And the plain OpenAI image service is wired

  Scenario: Fallback disabled
    Given IMAGE_BRIDGE_FALLBACK_ENABLED is false
    When the bridge job fails
    Then image generation raises the same RuntimeError contract as the OpenAI service
```

## Delta

### ADDED

- `backend/src/rag_backend/modules/image_bridge/` (domain, application, infrastructure, api,
  constants, public)
- Alembic migration for `image_bridge_jobs`
- `backend/tests/features/image_bridge.feature` + unit and Postgres tests
- `scripts/image_bridge_smoke.py`

### MODIFIED

- `infrastructure/container.py` (flagged wiring), `infrastructure/config/settings.py`
- the API router registration for the callback route
- `nginx/nginx.conf`, `nginx/nginx.conf.ssl`, `.env.example`, `.github/workflows/deploy.yml`

### REMOVED

- None.

## Affected Areas

- Backend: new module + container wiring
- Frontend: none
- Database: new table `image_bridge_jobs` (created at startup in prod; migration for dev/CI)
- API: new callback route
- Tests: feature + unit + PG tests
- Docs: architecture doc + ADR-0022 (already written)
- Prompts/LLM: none (prompts are sent as-is)
- Observability: `image_provider` field in logs/Langfuse metadata
- Deployment: new env vars in deploy.yml; nginx body size on the callback route

## Dependencies

- Blocks: enabling the bridge in prod
- Blocked by: none (the owner sets up the Grok Bot webhook in parallel)
- Related: ADR-0020 (GrokBot autopilot), ADR-0022, codex image spike (2026-10-15)

## Implementation Plan

1. Write the `.feature` first; then domain (models, callback parsing and validation) with unit tests.
2. Repository + migration + PG tests (poll, bytes round trip, expiry).
3. Webhook client (httpx, 15 s timeout) + `GrokBotImageService` (semaphore, wait loop,
   normalization) + `FallbackImageService`.
4. Callback route + auth + limits; register the router.
5. Settings, startup validation, container wiring, `.env.example`, `deploy.yml`, nginx.
6. Smoke CLI. Full gates; DB gates via the relay.

## QA Checklist

- [ ] Security reviewed (token handling, 401 uniformity, decode limits, no SSRF)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-15 19:40

Ticket created from the codex image spike and the owner's decision to use a Grok Bot webhook.

### 2026-10-15 (developer, Pi worktree)

- `.feature` first (`backend/tests/features/image_bridge.feature`, 18 scenarios), then the
  module `modules/image_bridge/` (domain → application → infrastructure → api → bootstrap/public,
  autopilot layout). Two new import-linter contracts (application isolation, public facade).
  The router stays off the facade (as in autopilot) so infrastructure never reaches the API layer.
- Callback route `POST /api/v1/image-bridge/jobs/{job_id}/result`: 413 on Content-Length or
  streamed body > 16 MB, the same 401 for bad/missing token, unknown job and non-UUID id, 409 for
  non-pending or overdue jobs (overdue is expired on the spot), 422 + job failed for malformed
  JSON / shapes / invalid images, 202 for an image or an OpenAI error body. b64_json only.
- Waiter: semaphore (`IMAGE_BRIDGE_MAX_CONCURRENCY`), lazy sweep, job + webhook (httpx, 15 s),
  2 s Postgres poll, conditional transitions (`WHERE status='pending'`), bytes read once and
  nulled, `ImageOps.fit` LANCZOS → PNG at exactly 1536x1024. Webhook metadata carries the
  carousel `project_id` from the run context when known.
- Owner update (same day): bridge ON in prod via `deploy.yml` with the OpenAI fallback; AC8
  replaced by "log one `image_bridge_misconfigured` ERROR and wire plain OpenAI" (no crash
  loop on auto-deploy). Design doc, ADR-0022, ticket ACs updated.
- Env parity: new `scripts/ci/check_image_bridge_env_parity.py` chained into
  `backend:autopilot-env` (4 surfaces, secret/plain split, deploy literals), with rule-fires tests.
- Migration `d3e4f5a6b7c8_image_bridge_jobs` (single head); the two migration tests that pinned
  the old head now pin the new one. Route snapshot regenerated (+1 route).

## Files Touched

- `backend/src/rag_backend/modules/image_bridge/**` (new module, 23 files)
- `backend/src/rag_backend/infrastructure/container.py` (flagged OpenAI-slot service),
  `infrastructure/config/settings.py` (8 settings), `infrastructure/database/models/__init__.py`
  + `image_bridge_registry.py`, `bootstrap/app_factory.py` (router), `bootstrap/startup_validation.py`
- `backend/alembic/versions/d3e4f5a6b7c8_image_bridge_jobs.py`, `backend/.importlinter`
- `backend/.env.example`, `.github/workflows/deploy.yml`, `docker-compose.prod.yml`,
  `nginx/nginx.conf`, `nginx/nginx.conf.ssl`
- `scripts/ci/check_image_bridge_env_parity.py`, `scripts/ci/gates.sh`, `scripts/image_bridge_smoke.py`
- Tests: `backend/tests/features/image_bridge.feature`, `backend/tests/unit/modules/image_bridge/*`,
  `backend/tests/unit/scripts_ci/test_check_image_bridge_env_parity.py`,
  `backend/tests/unit/scripts_ci/test_image_bridge_smoke.py`,
  `backend/tests/integration/test_image_bridge_migration.py`,
  `backend/tests/integration/test_image_bridge_repository_pg.py`,
  `backend/tests/integration/test_autopilot_migration.py`,
  `backend/tests/integration/test_content_mode_migration.py`, `backend/tests/snapshots/openapi_routes.json`
- Docs: `docs/architecture/grokbot-image-bridge.md`, `docs/decisions/0022-grokbot-image-bridge.md`

## Test Evidence

- Image bridge + touched areas: 185 passed, 4 skipped (the Postgres tests; relayed), module
  branch coverage 100% (732 stmts, 68 branches).
- Regression over 33 test files touching the container, registry, settings, startup: 348 passed.
- Static gates (Pi, individually via `gate-capture.sh`): 16/16 PASS — see
  `.agent/reports/AE-0393.dev-summary.md` for the GATES_JSON.
- Relayed to x86: DB gates (test, diff-cover, migrations, schema-drift), the PG tests, the
  Python 3.11 import check.

## QA Report

Pending.

## Decision Log

- 2026-10-15: Async webhook + callback behind `ImageGenerationService`, OpenAI fallback (ADR-0022).
- 2026-10-15 (owner): bridge ON by default in prod with the OpenAI fallback; AC8 changed from
  "fail at startup" to "log one ERROR and keep OpenAI" (no crash loop on auto-deploy).

## Blockers

None.

## Final Summary

Pending.
