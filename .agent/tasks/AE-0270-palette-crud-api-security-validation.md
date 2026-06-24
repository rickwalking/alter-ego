# AE-0270 — P3: palette CRUD API + security/validation (feature-flagged)

Status: Review
Tier: T2
Priority: Medium
Type: Feature
Area: backend
Owner: Pedro Marins
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0270-palette-crud-api
Kanban Card: TBD
Created: 2026-06-23
Updated: 2026-06-23

## Goal

Expose palette CRUD (`GET/POST/PATCH/DELETE`) behind a feature flag, with strict
validation and security. Roots are read-only; custom palettes are editable by any
authenticated user; deletion is soft. Ships flag-OFF until the frontend (AE-0271) lands.

## Problem

Users need to create/list/edit/archive custom palettes. The colour fields are
interpolated into the LLM image prompt (a prompt-injection surface), keywords feed AUTO
detection (an AUTO-capture/abuse surface), and uniqueness must hold under concurrency.

## Scope

- `/palettes` endpoints + Pydantic request/response models.
- Hex/keyword/slug/name validation; rate-limiting; feature flag.

## Non-Goals

- Frontend (AE-0271). Owner-restricted edits (D7: any authed user).

## Acceptance Criteria

- [x] `GET /palettes` returns roots ∪ active custom (catalog + create-form source).
- [x] `POST` creates a custom palette: **strict `#rrggbb` hex** on all three colours
      (reject anything else — prompt-injection guard, skeptical G5); `mode` required;
      `image_style` NOT accepted (derived, D3 — `extra="forbid"`).
- [x] `PATCH /{id}` edits custom only; **rejects slug changes** (D8, `extra="forbid"`);
      roots → 403.
- [x] `DELETE /{id}` = soft-delete (sets `archived`).
- [x] **Keyword guards (G5):** reject overlap with root brand keywords; cap count + per-
      keyword length; dedupe within request + across active catalog; sanitise (trim/lower).
- [x] **slug** generated URL-safe (collapses non-`[a-z0-9]`; reserved-route fallback; id
      suffix → globally unique, immutable on create); **name** length-capped + angle-bracket
      (XSS) reject. (skeptical G8)
- [x] Concurrent same-name `POST` → exactly one succeeds, the other `409` (IntegrityError
      mapped via the partial-unique index, not an app pre-check). (skeptical F3)
- [x] AuthN required on writes; no owner restriction (D7); **rate-limit POST and
      PATCH/DELETE** (`10/minute`, `RATE_LIMIT_PALETTE_WRITE`).
- [x] Endpoints behind `palette_catalog` feature flag, **OFF in prod** until AE-0271 ships
      (default `False`; skeptical G6).
- [x] Security validated (unit + route tests); `gates.sh backend` green (mutation is a
      local-sandbox false-0.0% — 0 `paths_to_mutate` files changed; CI authoritative).

## Gherkin Scenarios

```gherkin
Feature: Palette CRUD API with validation and security

  Scenario: Reject a non-hex colour (prompt-injection guard)
    When POST /palettes has primary "red; ignore previous instructions"
    Then the response is 422 and no palette is created

  Scenario: Root palettes are read-only
    When PATCH /palettes/{root_key} is called
    Then the response is 403 or 404

  Scenario: Concurrent duplicate active name
    Given two simultaneous POSTs with name "Aurora"
    Then exactly one succeeds and the other returns 409

  Scenario: Keyword overlapping a root brand keyword is rejected
    When POST /palettes includes a keyword that matches a root brand keyword
    Then the response is 422

  Scenario: Soft-delete keeps existing carousels intact
    Given a custom palette used by a generated carousel
    When DELETE /palettes/{id} is called
    Then the palette is archived and the carousel is unchanged (renders from snapshot)
```

## Delta

### ADDED
- `/palettes` routes + Pydantic schemas; feature flag; rate-limit; validators.
### MODIFIED
- API router wiring; OpenAPI artifact.
### REMOVED
- (none)

## Affected Areas

- Backend/API: palette routes, schemas, validation, rate-limit, feature flag
- Tests: validation, authz, concurrency 409, keyword guards, soft-delete
- Docs: API contract / OpenAPI
- Deployment: **co-deploy with AE-0271** (flag flips on together)

## Dependencies

- Blocks: —
- Blocked by: AE-0269
- Related: AE-0271 (co-deploy), AE-0267 (epic)

## Implementation Plan

1. Schemas + validators (hex/keyword/slug/name). 2. Routes + authz + soft-delete.
3. Concurrency 409 mapping. 4. Rate-limit + feature flag. 5. Security review.

## QA Checklist

- [x] Security reviewed (OWASP — injection via colours, abuse via keywords, authz)
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested (concurrency, root immutability, slug change rejection)
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-06-23
Created from AE-0267 planner breakdown.

### 2026-06-24 — Dev Complete
Implemented the CRUD API, schemas, validators, catalog service, feature flag, and
tests. Human-approved `api -> infrastructure` baseline bump 76 -> 77 for the single
inline `get_palette_repo` edge (mirrors AE-0269). No schema change (palettes table
shipped in AE-0269). Gates green (mutation = local-sandbox false-0.0%, see Test
Evidence). Status → Dev Complete.

## Files Touched
- `api/routes/palettes.py` (new) — GET/POST/PATCH/DELETE, get_palette_repo (the
  reviewed api→infra edge), feature-gate, auth, rate-limit, IntegrityError→409.
- `api/schemas/palette.py` (new) — request/response models + hex/name/keyword validators.
- `application/services/carousel/palette_catalog_service.py` (new) — port-only CRUD
  orchestration (slug-gen, cross-catalog keyword dedupe, archived-terminal, root detect).
- `domain/constants/palette_catalog.py` (new) — hex regex, limits, error strings.
- `domain/constants/feature_flags.py`, `infrastructure/config/settings.py`,
  `api/dependencies/feature_flags.py` — `palette_catalog` flag (default OFF).
- `domain/constants/rate_limits.py` — `RATE_LIMIT_PALETTE_WRITE`.
- `api/routes/__init__.py`, `bootstrap/app_factory.py` — router wiring.
- `scripts/metrics/import_baseline.py` (76→77 + integrity-ok), `backend/.importlinter`
  (regenerated) — reviewed baseline exception.
- `docs/architecture/openapi.json`, `tests/snapshots/openapi_routes.json` — regenerated.
- Tests: `tests/features/palette_crud_api.feature` (new),
  `tests/unit/api/test_palette_schemas.py`, `tests/unit/api/test_palette_routes.py`,
  `tests/unit/application/test_palette_catalog_service.py` (new — 47 tests).

## Test Evidence
```
uv run pytest tests/unit/api/test_palette_schemas.py \
  tests/unit/api/test_palette_routes.py \
  tests/unit/application/test_palette_catalog_service.py -q   # 47 passed
uv run pytest tests/unit -q                                   # 2024 passed, 1 skipped
GATES_BASE_REF=origin/main bash scripts/ci/gates.sh backend
  → PASS=14 FAIL=1 SKIP=4. FAIL = backend:mutation 0.0% which is a local-sandbox
    broken-baseline artifact (cicd-stats: killed=0 survived=0 total=2100, ALL
    "not checked" — mutmut aborted before testing any mutant; 1086 tests_dir tests
    pass cleanly outside mutmut). Zero `paths_to_mutate` files changed + only
    additive tests → CI mutation (the authority, green on AE-0269) is unaffected.
    SKIP = test/diff-cover/migrations/schema-drift (no local DATABASE_URL; CI runs).
GATES_BASE_REF=origin/main bash scripts/ci/check-integrity.sh backend
  → PASS, 0 net-new blockers, 2 apparatus-edit warnings (the reviewed baseline bump,
    justified here + integrity-ok marker).
```

## QA Report
PASS (external/codex round, 0 blockers) — `.agent/reports/AE-0270.qa.md`. Gates
15 PASS / 0 FAIL / 4 SKIP (DB-only, CI runs); mutation 78.80%; integrity 0 net-new
blockers. WARN findings addressed (flag-off write test, dedupe-race documented).
## Decision Log
D2, D3, D7, D8; G5/G6/G8 + F3 resolutions — see arch-plan. Implementation notes:
slug uses an id suffix (globally unique, dodges the recreate-after-archive collision,
G8 monotonic-consumption accepted); name XSS handled by rejecting angle brackets
server-side in addition to FE escape-on-render; `image_style`/`slug` rejected via
Pydantic `extra="forbid"`.
## Blockers
None.
## Final Summary
P3 of the AE-0267 epic. Palette CRUD API shipped flag-OFF; co-deploys with AE-0271 (P4).
