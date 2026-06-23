# AE-0270 — P3: palette CRUD API + security/validation (feature-flagged)

Status: Ready
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

- [ ] `GET /palettes` returns roots ∪ active custom (catalog + create-form source).
- [ ] `POST` creates a custom palette: **strict `#rrggbb` hex** on all three colours
      (reject anything else — prompt-injection guard, skeptical G5); `mode` required;
      `image_style` NOT accepted (derived, D3).
- [ ] `PATCH /{id}` edits custom only; **rejects slug changes** (D8); roots → 403/404.
- [ ] `DELETE /{id}` = soft-delete (sets `archived`).
- [ ] **Keyword guards (G5):** reject overlap with root brand keywords; cap count + per-
      keyword length; dedupe across active catalog; sanitise.
- [ ] **slug** generated URL-safe (reject `/`, `..`, reserved routes), immutable on create;
      **name** length-capped + escaped-on-render (XSS). (skeptical G8)
- [ ] Concurrent same-name `POST` → exactly one succeeds, the other `409` (IntegrityError
      mapped, not an app pre-check). (skeptical F3)
- [ ] AuthN required on writes; no owner restriction (D7); **rate-limit POST and
      PATCH/DELETE** (per-user/per-palette).
- [ ] Endpoints behind a feature flag, **OFF in prod** until AE-0271 ships (skeptical G6).
- [ ] Security review passed; full `gates.sh backend` green.

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

- [ ] Security reviewed (OWASP — injection via colours, abuse via keywords, authz)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (concurrency, root immutability, slug change rejection)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-23
Created from AE-0267 planner breakdown.

## Files Touched
Pending.
## Test Evidence
Pending.
## QA Report
Pending.
## Decision Log
D2, D3, D7, D8; G5/G6/G8 + F3 resolutions — see arch-plan.
## Blockers
None.
## Final Summary
Pending.
