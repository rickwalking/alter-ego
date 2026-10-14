# AE-0351 — Scoped service API key auth for /api/autopilot/*

Status: Review
Tier: T2
Priority: High
Type: Feature
Area: backend
Owner: Grok (Cursor CLI, grok-4.7-high)
Agent Lane: developer → qa → release
Branch: feat/ae-0351-autopilot-service-api-key-auth
Kanban Card: TBD
Created: 2026-10-13
Updated: 2026-10-13
Parent: AE-0348

## Goal

Allow the host scout to call `/api/autopilot/*` with an `X-Api-Key` header, without a user JWT, and only on those routes.

## Problem

Auth today is HS256 JWT only (`infrastructure/auth.py`), 60-min expiry, no refresh; a bot would need a user password and hourly re-login.

## Scope

- Setting `GROKBOT_API_KEY_SHA256` (hex digest; plaintext never stored server-side).
- FastAPI dependency `require_autopilot_api_key` in `modules/autopilot/api/auth.py`: reads `X-Api-Key`, sha256, `hmac.compare_digest` against the setting; 401 on missing/mismatch; 503 if the setting is unset (feature disabled).
- Applied ONLY to the `/api/autopilot/*` router; it never grants a user identity and never works on other routes.
- Rate limit 10/min per IP on autopilot routes (slowapi, constant in `domain/constants/rate_limits.py` style).

## Non-Goals

- General-purpose API keys, key rotation UI, multiple keys.

## Acceptance Criteria

- [x] WHEN a request to `/api/autopilot/signals` has a valid key THE API SHALL return 200.
- [x] WHEN the key is missing or wrong THE API SHALL return 401 and log a warning without the key value.
- [x] WHEN the key is valid but the route is outside `/api/autopilot/*` (e.g. `/api/carousels`) THE API SHALL still return 401.
- [x] WHEN `GROKBOT_API_KEY_SHA256` is unset THE autopilot routes SHALL return 503.

## Gherkin Scenarios

```gherkin
Feature: Autopilot service API key

  Scenario: Valid key accesses autopilot routes
    Given the server is configured with the sha256 of key "k1"
    When the scout calls GET /api/autopilot/signals with X-Api-Key "k1"
    Then the response status is 200

  Scenario: Wrong key is rejected
    When the scout calls GET /api/autopilot/signals with X-Api-Key "nope"
    Then the response status is 401

  Scenario: Key does not unlock other routes
    When the scout calls GET /api/carousels with X-Api-Key "k1"
    Then the response status is 401

  Scenario: Feature disabled
    Given no autopilot key hash is configured
    When the scout calls GET /api/autopilot/signals with X-Api-Key "k1"
    Then the response status is 503
```

## Delta

### ADDED

- `backend/src/rag_backend/modules/autopilot/api/auth.py`
- Setting `grokbot_api_key_sha256`
- `backend/tests/features/autopilot_api_key.feature`

### MODIFIED

- `infrastructure/config/settings.py`
- `backend/.env.example`

### REMOVED

- None.

## Affected Areas

- Backend: auth dependency
- API: header auth
- Tests

## Dependencies

- Blocks: AE-0352, AE-0353, AE-0360
- Blocked by: AE-0350
- Related: AE-0359 (secret wiring)

## Implementation Plan

1. Feature file first.
2. Dependency + constants.
3. Mount on autopilot router only; add a test that walks `app.routes` and asserts the dependency appears only under `/api/autopilot`.

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
- [ ] Constant-time compare verified
- [ ] Key never logged

## Progress Log

### 2026-10-13 00:00

Ticket created from docs/architecture/grokbot-autopilot.md (ticket #2).

### 2026-10-13 17:20

In Development on `feat/ae-0351-autopilot-service-api-key-auth`. Feature file written first, then the scoped dependency, router, and tests.

### 2026-10-13 17:58

`bash scripts/ci/gate-capture.sh backend` exit 0 (20 pass, 0 fail, 0 skip). Pytest 2985 passed / 2 skipped. Dev summary: `.agent/reports/AE-0351.dev-summary.md`.

### 2026-10-13 18:05

Moved to Dev Complete. Post-commit integrity scan: 0 blockers, same two AE-0350 apparatus warnings.

## Files Touched

- `backend/tests/features/autopilot_api_key.feature`
- `backend/tests/integration/test_autopilot_api_key.py`
- `backend/src/rag_backend/modules/autopilot/api/auth.py`
- `backend/src/rag_backend/modules/autopilot/api/router.py`
- `backend/src/rag_backend/modules/autopilot/api/__init__.py`
- `backend/src/rag_backend/modules/autopilot/constants.py`
- `backend/src/rag_backend/domain/constants/rate_limits.py`
- `backend/src/rag_backend/infrastructure/config/settings.py`
- `backend/src/rag_backend/bootstrap/app_factory.py`
- `backend/tests/snapshots/openapi_routes.json`
- `backend/.env.example`

## Test Evidence

- `backend/tests/features/autopilot_api_key.feature` — valid key, wrong key, missing key, other routes, public carousel list, disabled feature, shared rate limit, dependency scope.
- `tests/integration/test_autopilot_api_key.py` — those scenarios, plus empty header, padded/uppercase digest, malformed digest (401, not 500), and `hmac.compare_digest` called with the hex digests.
- Gate proof: `.agent/reports/AE-0351.dev-summary.md`.

## QA Report

Pending.

## Decision Log

See ADR-0020.

### 2026-10-13

- The stored verifier is the sha256 hex digest in `GROKBOT_API_KEY_SHA256`, compared with `hmac.compare_digest`. The architecture gap table also says "argon2/sha256" and `GROKBOT_API_KEY_HASH`. This ticket and AE-0359 both name `GROKBOT_API_KEY_SHA256`, and the ticket specifies sha256. Argon2 is not used.
- `GET /api/carousels` (the list) is anonymous-public and stays 200. The key does not attach a user. Routes that already require a user still return 401: `GET /api/documents` and `GET /api/carousels/{project_id}`.
- `GET /api/autopilot/signals` returns `{}` until AE-0352 fills the bundle. This ticket only mounts the route so the key can be enforced.
- The HTTP router is included from the composition root (`bootstrap/app_factory.py`), not re-exported on the package facade. Model registration imports the facade; putting the router there would make infrastructure depend on `rag_backend.api` through the shared slowapi limiter.

## Blockers

None.

## Final Summary

Pending.
