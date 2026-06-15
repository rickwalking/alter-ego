# AE-0099 — Auth + admin routes behind identity handlers (byte-identical cookies/JWT)

Status: Dev Complete
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0099-identity-routes
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Move `auth.py` + `admin.py` endpoint logic behind identity application handlers via the facade; routes become thin adapters. Cookies, JWT payloads, and bcrypt stay byte-identical.

## Problem

Auth/admin routes contain business logic and access user persistence directly. Phase 3 makes them thin adapters delegating to the AE-0098 identity facade.

## Scope

- Each /api auth endpoint (token/login, logout, me, change-password) and admin endpoint (user CRUD, reset-password, role-assign) delegates to an identity handler via the facade.
- Routes resolve the facade via DI at the edge; they do not import PostgresUserRepository or get_container for user ops.
- Preserve Set-Cookie attributes (access_token httponly/secure/samesite/max_age), the HS256 JWT payload, bcrypt, status codes, and response shapes EXACTLY.
- User writes commit via the platform UoW (single owner).

## Non-Goals

- No cookie/JWT/contract changes.
- No renames.

## Modularization Alignment (2026-06-15)

Phase 3 of the modularization plan (§Phase 3). **Behavior-preserving** — cookies (access_token/anon_token), HS256 JWT payloads, bcrypt, URLs, and SSE event payloads/keep-alive/Last-Event-ID/X-Agent-Origin stay byte-identical; NO renames (Phase 4+). Follow `docs/architecture/module-conventions.md` + `modules/_template`; reuse the Phase-2 `platform/database` UoW, the AE-0093 `KnowledgeSearchPort`, and the knowledge facade; compose via DI at the edge (no get_container in module code). `api/middleware/auth.py`, `infrastructure/auth.py`, and `api/dependencies/resource_access.py` stay at root (shared). Precondition: Phase 2 (PR #16) merged. Gated on the AE-0097 snapshots (cookies + JWT shape) diffing to zero.

## Acceptance Criteria

- [ ] EACH auth/admin endpoint SHALL delegate to an identity handler via the facade
- [ ] WHEN any auth/admin endpoint is called THE response (incl. Set-Cookie attributes + JWT payload) SHALL diff to ZERO against the AE-0097 snapshots
- [ ] THE auth/admin routes SHALL NOT import PostgresUserRepository or get_container (resolved via facade/DI)
- [ ] User write endpoints SHALL persist via the platform UoW; routes SHALL NOT call `db.commit()`/`session.commit()` directly (UoW is the single committer; ratchets api->infrastructure down)
- [ ] WHEN gates.sh + mypy + lint-imports + pytest run THEY SHALL pass; AE-0097 safety net green

## Gherkin Scenarios

```gherkin
Feature: Auth endpoints unchanged after extraction

  Scenario: login response byte-identical
    Given valid credentials
    When POST /api/auth/token runs through the identity handler
    Then the response + access_token cookie diff to zero against the snapshot
```

## Delta

### ADDED

- identity command/query handlers for auth+admin

### MODIFIED

- api/routes/auth.py, api/routes/admin.py (thin adapters via facade)
- api/dependencies/auth.py (delegate to identity facade)

### REMOVED

- None

## Affected Areas

- Backend: handlers + routes
- Frontend: none
- Database: none
- API: unchanged contract
- Tests: endpoint parity
- Docs: none
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0103
- Blocked by: AE-0097, AE-0098
- Related: resource_access (shared)

## Implementation Plan

1. Add identity handlers behind the facade.
2. Convert auth/admin routes to delegate (one at a time).
3. Writes via UoW; cookies/JWT identical; snapshot diff=0.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 3 breakdown).

Dev Complete (Wave B). auth+admin routes → identity handlers via facade; byte-identical (AE-0097 diff=0); UoW single committer; arch-ratchet improved (api->infra 98→83, get_container 26→16). mypy 460, lint-imports 10/0, integrity 0 blockers.

## Files Touched

api/routes/auth.py, api/routes/admin.py, api/dependencies/auth.py, api/dependencies/identity.py, modules/identity/application/{auth_handlers,admin_handlers}.py, modules/identity/{bootstrap,public,constants}.py, tests/unit/modules/identity/test_identity_handlers.py

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
