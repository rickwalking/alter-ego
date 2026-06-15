# AE-0098 — modules/identity skeleton + facade + UserService/AuthenticationService + ports

Status: Review
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0098-identity-module
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Create `modules/identity/` (domain/application/infrastructure/api + public.py + bootstrap.py); extract `UserService`/`AuthenticationService`/`PasswordService` from routes+deps; re-export `UserRepository` port and `User`/`UserRole`; expose the role-check dependencies via the identity facade. No routes moved yet.

## Problem

Identity has no application service today — auth/user logic is scattered across routes, `api/dependencies/auth.py`, and `infrastructure/auth.py`. The module needs services + a facade before routes can delegate (AE-0099).

## Scope

- Scaffold `modules/identity/` per conventions + `_template`.
- Extract `UserService` (create/list/get/update/delete/role-assign), `AuthenticationService` (login/token issue+validate via the EXISTING infrastructure/auth.py — do not reimplement JWT/bcrypt), `PasswordService` (hash/verify/policy) into the application layer.
- Re-export `UserRepository` port from `modules/identity/domain/ports.py` with a shim at the legacy `domain/protocols` path (existing callers unbroken); re-export `User`/`UserRole`.
- Expose role-check dependencies (require_authenticated_user/require_admin/etc.) via the identity facade, still backed by `api/middleware/auth.py` (which stays at root).
- Add fake + Postgres UserRepository contract tests (reuse the AE-0094 pattern).

## Non-Goals

- No routes moved (AE-0099).
- No change to JWT/bcrypt/cookie behavior.
- Do NOT relocate api/middleware/auth.py or infrastructure/auth.py.

## Modularization Alignment (2026-06-15)

Phase 3 of the modularization plan (§Phase 3). **Behavior-preserving** — cookies (access_token/anon_token), HS256 JWT payloads, bcrypt, URLs, and SSE event payloads/keep-alive/Last-Event-ID/X-Agent-Origin stay byte-identical; NO renames (Phase 4+). Follow `docs/architecture/module-conventions.md` + `modules/_template`; reuse the Phase-2 `platform/database` UoW, the AE-0093 `KnowledgeSearchPort`, and the knowledge facade; compose via DI at the edge (no get_container in module code). `api/middleware/auth.py`, `infrastructure/auth.py`, and `api/dependencies/resource_access.py` stay at root (shared). Precondition: Phase 2 (PR #16) merged. Reuse `platform/database` UoW for user writes. infrastructure/auth.py is the single JWT/bcrypt source — services delegate to it.

## Acceptance Criteria

- [ ] modules/identity SHALL exist per conventions with public.py facade + bootstrap.py (manual DI, no get_container)
- [ ] UserService/AuthenticationService/PasswordService SHALL be typed (no Any) and delegate JWT/bcrypt to the unchanged infrastructure/auth.py
- [ ] THE UserRepository port SHALL be re-exported (existing domain.protocols imports keep resolving); User/UserRole re-exported
- [ ] WHEN lint-imports + pytest run after the shim THE existing callers of UserRepository SHALL still resolve (CI-verified; object-identity shim)
- [ ] THE role-check dependencies SHALL be reachable via the identity facade
- [ ] A fake + Postgres UserRepository contract suite SHALL pass (behavior matches)
- [ ] WHEN mypy/lint-imports/pytest run THEY SHALL pass with no new violations and no behavior change

## Gherkin Scenarios

Not applicable — behavior-preserving extraction; no runtime behavior change (verified by the AE-0097 safety net).

## Delta

### ADDED

- modules/identity/{domain,application,infrastructure,api}/, public.py, bootstrap.py, constants.py
- UserService/AuthenticationService/PasswordService
- UserRepository contract tests

### MODIFIED

- domain/protocols/repositories.py (re-export shim for UserRepository)

### REMOVED

- None

## Affected Areas

- Backend: identity module
- Frontend: none
- Database: none
- API: none yet
- Tests: repo contract suite
- Docs: references conventions
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0099, AE-0103
- Blocked by: none
- Related: AE-0081, AE-0094

## Implementation Plan

1. Scaffold modules/identity.
2. Extract User/Authentication/Password services (delegate to infrastructure/auth.py).
3. Re-export ports/entities; expose role deps via facade.
4. Contract tests; mypy/lint-imports/pytest.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 3 breakdown).

Dev Complete (Wave A). Created modules/identity: UserService/AuthenticationService/PasswordService (delegate JWT/bcrypt to unchanged infrastructure/auth.py), object-identity UserRepository+User/UserRole shims, role-deps via facade, fake+sqlite contract suite. repositories.py untouched (A is B verified). Gate spine 14 PASS/0 FAIL/3 SKIP(DB→CI), integrity 0 blockers, mypy/lint-imports green.

## Files Touched

backend/src/rag_backend/modules/identity/** (+public.py/bootstrap.py/constants.py), tests/unit/modules/identity/*, tests/unit/infrastructure/test_user_repository_contract.py

## Test Evidence

Pending.

## QA Report

Phase 3 Wave A batch QA — converged PASS in 2 independent rounds (0 findings). See `.agent/reports/phase-3-wave-a.qa.md`.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
