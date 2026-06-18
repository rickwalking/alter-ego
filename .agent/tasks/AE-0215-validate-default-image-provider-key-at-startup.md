# AE-0215 — Validate default image-provider key at startup

Status: Done
Tier: T1
Priority: Medium
Type: Quality
Area: backend
Owner: Unassigned
Branch: TBD
Created: 2026-06-18
Updated: 2026-06-18

## Goal

The default image-provider's API key is validated at startup so a default-preset carousel can't fail at image generation.

Source: Kaizen prod sweep `.agent/reports/kaizen-prod-2026-06-18.plan.md` (live carousel run, project b5b61790-9372-4a5a-ae17-30d2df28ef3d), validated by an independent architect cold-critic review.

## Problem

`constants/carousel.py:104-105` sets `IMAGE_MODEL_DEFAULT=gemini`, `IMAGE_STYLE_DEFAULT=comic_neon` (DB server_default also gemini/comic_neon), but prod `GEMINI_API_KEY` is empty. `app_factory` validates pinecone/openai keys for RAG but NOT the default image-provider key — so a carousel using the default preset would fail at image gen in prod.

## Scope

- Validate at startup that the configured/default image-provider has a usable key (fail fast or disable that preset with a clear message); or change the default preset to a provider with a configured key.
- Test: the default preset's provider key is required/validated.

## Non-Goals

- Procuring the Gemini key (ops decision).

## Acceptance Criteria

- [x] Startup validation covers the default image-provider key (fail-fast or preset disabled). (Code: `bootstrap/startup_validation.py::validate_default_image_provider_key` — fail-fast in production-like env; warns + treats preset as disabled in dev/test.)
- [x] Test proves the default-preset provider key is validated. (`tests/unit/bootstrap/test_startup_validation.py`.)

## Repro Steps

1. Run with `ENVIRONMENT=production` and empty `GEMINI_API_KEY` (default image
   provider is gemini): startup now raises `StartupValidationError` instead of
   failing later at image generation.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

- Blocks: —
- Blocked by: —
- Related: AE-0119 (image provider ports)

## Progress Log

### 2026-06-18 HH:mm

Ticket created.

### 2026-06-18 dev

Added `validate_default_image_provider_key` to the composition-root startup
hardening module (shared with AE-0213). Default provider (`gemini`) key must be
present in production-like environments or startup fails fast; dev/test warns and
treats the default preset as disabled. Seeded tests pass. See
`.agent/reports/AE-0215.dev-summary.md`.

## Files Touched

- `backend/src/rag_backend/bootstrap/startup_validation.py`
- `backend/.env.example`
- `backend/tests/features/startup_hardening.feature`
- `backend/tests/unit/bootstrap/test_startup_validation.py`

## Test Evidence

```bash
uv run pytest tests/unit/bootstrap/ -q
# 12 passed
```

Seeded tests (AE-0215 portion):
- `test_prod_missing_default_image_key_raises` — prod + empty gemini key → raise.
- `test_prod_present_default_image_key_passes` — prod + key present → pass.
- `test_dev_missing_default_image_key_warns_not_raises` — dev + empty key → warn.
- `test_run_startup_validations_prod_missing_image_key_raises` — runner fails fast.

Gates: full backend run `GATES_JSON: {"pass":14,"fail":0,"skip":3,...}` (DB gates
SKIP locally; test/diff-cover verified PASS with DATABASE_URL set; migrations SKIP
— no models touched). Integrity: 0 net-new blockers. arch-ratchet PASS.

## QA Report

Pending.

## Blockers

None.

## Final Summary

Shipped in PR #48. Startup validation of the default image-provider key (default gemini→`GEMINI_API_KEY`): fail-fast in prod, warn + treat preset disabled in dev. Seeded tests. Operator action pending: set prod `GEMINI_API_KEY` (or change the default preset) + `ENVIRONMENT=production`.
