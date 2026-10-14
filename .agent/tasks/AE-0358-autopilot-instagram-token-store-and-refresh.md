# AE-0358 — Instagram token store (encrypted) + 50-day auto-refresh + expiry alert

Status: Dev Complete
Tier: T2
Priority: High
Type: Feature
Area: backend
Owner: Grok (Cursor CLI, grok-4.7-high)
Agent Lane: developer → qa → release
Branch: feat/ae-0358-autopilot-instagram-token-store-and-refresh
Kanban Card: TBD
Created: 2026-10-13
Updated: 2026-10-14
Parent: AE-0348

## Goal

Keep the Instagram long-lived token alive automatically; alert the owner before it can expire.

## Problem

The token is a static env var (`META_IG_ACCESS_TOKEN`); long-lived tokens expire after 60 days and cannot be recovered once expired.

## Scope

- `integration_credentials` row `provider=instagram`; token encrypted at rest with Fernet key `CREDENTIALS_ENCRYPTION_KEY` (use `cryptography` if already a dependency; otherwise add it — record in Decision Log).
- Seed: if no row exists and `META_IG_ACCESS_TOKEN` is set, insert it with `expires_at = now + 60d` (conservative) on startup.
- `InstagramTokenProvider.get()` used by AE-0357 publisher.
- Daily worker step: if `refreshed_at` older than 50 days (or `expires_at` < now+10d) → `GET https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=…`; store new token + `expires_in`.
- Refresh failure → retry daily; Telegram alert when `expires_at` < now+7d or on 190 (invalid token) error, with manual-regeneration instructions link to the doc.

## Non-Goals

- OAuth login flow UI.
- Facebook-Login (Page token) path.

## Acceptance Criteria

- [x] WHEN the token is 50 days old THE worker SHALL refresh it and persist the new expiry.
- [x] WHEN refresh fails and expiry is <7 days away THE owner SHALL receive a Telegram alert once per day.
- [x] WHEN the DB row is read raw THE token SHALL NOT appear in plaintext.
- [x] WHEN no token is configured THE publish job SHALL fail fast with reason `instagram_token_missing`.

## Gherkin Scenarios

```gherkin
Feature: Instagram token lifecycle

  Scenario: Token refreshed before expiry
    Given the stored token was refreshed 51 days ago
    When the daily credential step runs
    Then the token is refreshed and expires_at moves forward

  Scenario: Refresh keeps failing near expiry
    Given refresh fails and the token expires in 5 days
    When the daily credential step runs
    Then the owner receives a Telegram alert
```

## Delta

### ADDED

- `backend/src/rag_backend/modules/autopilot/infrastructure/credential_store.py`
- `backend/src/rag_backend/modules/autopilot/application/token_refresher.py`
- `backend/tests/features/autopilot_ig_token.feature`

### MODIFIED

- settings: `credentials_encryption_key`
- worker tick (daily-gated step)

### REMOVED

- None.

## Affected Areas

- Backend
- Security: encryption at rest
- Tests

## Dependencies

- Blocks: AE-0359
- Blocked by: AE-0357

## Implementation Plan

1. Feature first.
2. Store + provider + refresher with respx tests.
3. Wire into worker with a once-per-day guard.

## Implementer Notes (read first — Cursor CLI / Grok)

- Source of truth: [docs/architecture/grokbot-autopilot.md](../../docs/architecture/grokbot-autopilot.md) and [ADR-0020](../../docs/decisions/0020-grokbot-autopilot.md). If this ticket and the doc disagree, STOP and ask — do not guess.
- Read `CLAUDE.md`, `backend/CLAUDE.md`, `backend/AGENTS.md`, `docs/architecture/module-conventions.md` before coding.
- Module rules: new code lives in `backend/src/rag_backend/modules/autopilot/` following `modules/_template/` (domain/application/infrastructure/api + `public.py` + `bootstrap.py` + `constants.py`). Other modules are reached ONLY through their `public.py`; add an import-linter contract for `autopilot` (module-conventions §7a/§7d).
- Hard rules: no magic strings (constants.py), no `Any`/`object`, ≤3 args per function (Pydantic/typed command objects), guard clauses, ≤400 lines/file, mypy strict, ruff clean, 90%+ branch coverage.
- Behavior-changing tickets: write the `.feature` file FIRST under `backend/tests/features/` and reference scenario names in test comments.
- Never commit secrets. Never push `main` (auto-deploys prod). Branch per ticket, lowercase conventional commits.
- Done = `bash scripts/ci/gate-capture.sh backend` green with the `GATES_JSON:` line pasted in the dev summary + `/qa-agent` PASS. Never pipe gates to `tail`/`head`.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked
- [ ] Token never logged
- [ ] Encryption key absence → explicit startup warning, autopilot publishing disabled

## Progress Log

### 2026-10-13 00:00

Ticket created from docs/architecture/grokbot-autopilot.md (ticket #9).

### 2026-10-14

Moved to In Development. Encrypted store, startup seed, daily refresh, and the expiry alert are implemented. `bash scripts/ci/gate-capture.sh backend` exit 0 (16 pass, 0 fail, 4 skip). See `.agent/reports/AE-0358.dev-summary.md`.

## Files Touched

- `backend/tests/features/autopilot_ig_token.feature`
- `backend/src/rag_backend/modules/autopilot/credential_constants.py`
- `backend/src/rag_backend/modules/autopilot/domain/credential_ports.py`
- `backend/src/rag_backend/modules/autopilot/domain/token_refresh.py`
- `backend/src/rag_backend/modules/autopilot/domain/models.py`
- `backend/src/rag_backend/modules/autopilot/application/credential_seed.py`
- `backend/src/rag_backend/modules/autopilot/application/day_gate.py`
- `backend/src/rag_backend/modules/autopilot/application/token_refresher.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/credential_cipher.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/credential_store.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/instagram_token_client.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/token_alert.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/stored_token_provider.py`
- `backend/src/rag_backend/modules/autopilot/bootstrap_credentials.py`
- `backend/src/rag_backend/modules/autopilot/public.py`
- `backend/src/rag_backend/modules/autopilot/__init__.py`
- `backend/src/rag_backend/infrastructure/config/settings.py`
- `backend/src/rag_backend/infrastructure/external/instagram_publisher_factory.py`
- `backend/src/rag_backend/infrastructure/external/instagram_token.py`
- `backend/src/rag_backend/infrastructure/external/meta_instagram_publisher.py`
- `backend/src/rag_backend/domain/protocols/instagram_token.py`
- `backend/src/rag_backend/application/workers/workflow_workers.py`
- `backend/src/rag_backend/bootstrap/app_factory.py`
- `backend/.env.example`
- `backend/tests/unit/modules/autopilot/test_token_lifecycle.py`
- `backend/tests/unit/modules/autopilot/test_credential_store.py`
- `backend/tests/unit/modules/autopilot/test_token_refresher.py`
- `backend/tests/unit/application/test_workflow_workers.py`
- `backend/tests/unit/infrastructure/test_meta_instagram_publisher.py`
- `backend/tests/unit/modules/autopilot/test_instagram_publish_job.py`

## Test Evidence

- `backend/tests/features/autopilot_ig_token.feature` — refresh, once-per-day alert and retry, error 190, ciphertext, missing token, seed, missing key, token never logged.
- Focused pytest: **80 passed** (`test_token_lifecycle`, `test_credential_store`, `test_token_refresher`, `test_workflow_workers`, `test_meta_instagram_publisher`, `test_instagram_publish_job`).
- `cd backend && uv run alembic heads` → single head `f2a3b4c5d6e7`.
- `bash scripts/ci/gate-capture.sh backend` exit 0. Mutation score 79.98%.

## QA Report

Pending.

## Decision Log

See ADR-0020.

- `cryptography` is already a dependency (`cryptography>=48.0.1`, locked at 50.0.1). Fernet is used. No package was added.
- Seed writes `refreshed_at = now` as well as `expires_at = now + 60d`. A null refresh clock is not treated as older than 50 days.
- Once per day is an in-memory America/Sao_Paulo gate on the process-lived adapter. A restart can run the step again the same day. No new column.
- Refresh uses the unversioned `https://graph.instagram.com/refresh_access_token` with proxies and redirects off.
- The owner alert is a direct Telegram `sendMessage`, not `content.autopilot.ig_token_expiring`, because that event requires an autopilot run id. The message links to Meta's Instagram Login business-login doc.
- A missing or invalid key logs a warning and skips registering Instagram publish and credential refresh. Publishing fails fast with `instagram_token_missing`. Startup is not aborted.
- A publish `get()` in the same worker tick can still see the previous token. The next tick sees the refreshed one.
- Age `>= 50` days matches "50 days old" and the 51-day scenario. The 10-day and 7-day windows are strict less-than.

## Blockers

- Manual (Pedro): generate `CREDENTIALS_ENCRYPTION_KEY` (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`) and set it in the runtime environment. GitHub Secrets, `deploy.yml`, and `docker-compose.prod.yml` belong to AE-0359.
- Manual (Pedro): set `META_IG_ACCESS_TOKEN` on the first boot that has a usable encryption key so the row can be seeded. After that the database row is the source of truth.

## Final Summary

The Instagram token is encrypted at rest, seeded once from the env var, refreshed on a daily worker step, and the owner is alerted on Telegram when refresh fails near expiry or Meta returns error 190. Gate capture is green (16 pass, 0 fail, 4 skip).
