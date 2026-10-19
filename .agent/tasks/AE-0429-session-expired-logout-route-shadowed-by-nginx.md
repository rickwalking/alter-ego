# AE-0429 — Expired session redirects to a backend 405 JSON page instead of /login

Status: Dev Complete
Tier: T2
Priority: P1
Type: Bug
Area: Frontend
Owner: Claude (owner-reported prod bug, 2026-10-19)
Agent Lane: developer → qa → release
Branch: feat/ae-0429-session-expired-logout-route
Kanban Card: TBD
Created: 2026-10-19
Updated: 2026-10-19

## Goal

When the access token expires, the browser clears the stale HttpOnly cookie and lands on
`/login?redirect=<path>&error=session_expired` — never on a backend JSON `405` page.

## Problem

Owner report (prod, 2026-10-19): after the token expired the user was sent to

```
https://marinssolutions.com/api/auth/logout?redirect=%2Fdashboard%2Fcreate%2F<id>%3Fstep%3Dcontent
```

A prod `GET` to that URL returns `405 {"detail":"Method Not Allowed"}`.

Root cause (verified on `origin/main`):

- `frontend/src/lib/api-client.ts` redirected a 401 to `/api/auth/logout?redirect=…`.
- The intended handler was the Next route `frontend/src/app/api/auth/logout/route.ts`
  (GET: clear the cookie, best-effort backend POST, redirect to `/login`).
- In prod nginx (`nginx/nginx.conf.ssl`, `location /api/ { proxy_pass
  http://backend/api/; }`) forwards **every** `/api/*` request to FastAPI, so the Next
  route never runs. FastAPI only exposes `POST /api/auth/logout`, hence GET → 405. The
  stale cookie was never cleared either.

## Scope

1. Add `PUBLIC_ROUTE_PATHS.LOGOUT = "/auth/logout"` (front-end route, outside `/api`) and
   point the 401 redirect in `api-client.ts` at it.
2. Move the GET handler from `src/app/api/auth/logout/route.ts` to
   `src/app/auth/logout/route.ts` with identical behaviour (clear `access_token`,
   best-effort backend POST, `sanitizeLoginRedirect`, `error=session_expired`).
3. Let the route through middleware unauthenticated: `isPublicRoute("/auth/logout")` and
   the `PUBLIC_ROUTES` inventory include it.
4. Keep `API_ENDPOINTS.AUTH_LOGOUT = "/api/auth/logout"` for the backend POST used by
   `modules/identity/queries.ts` (`useAuth.logout`).
5. Delete the shadowed Next route; regenerate `frontend/scripts/url-inventory.snapshot.json`.
6. Guard the regression: the api-client unit tests assert the redirect target is
   `/auth/logout` and is **not** under `/api/`; the guard test asserts the logout path is
   public and outside `/api/`.
7. Gherkin + tests: `frontend/tests/features/session-expired-redirect-ae0429.feature`
   (happy, open-redirect, no redirect param, backend failure, unauthenticated reachability).

### Follow-up (NOT in this ticket): the other three shadowed `app/api` routes

They are dead in prod for the same nginx reason, but today each is served by a same-path
FastAPI endpoint, so users do not see a 405:

| Next route | Prod behaviour today (nginx → FastAPI, `nginx/nginx.conf.ssl:203`) |
| --- | --- |
| `/api/auth/token` | `POST /api/auth/token` exists in FastAPI (`backend/tests/snapshots/openapi_routes.json`); the Next BFF handler never runs, so the `access_token` cookie is set by the backend response instead. |
| `/api/carousels/[id]/workflow/start` | `POST /api/carousels/{project_id}/workflow/start` exists in FastAPI (`editorial_workflow.py`). |
| `/api/carousels/[id]/workflow/resume` | `POST /api/carousels/{project_id}/workflow/resume` exists in FastAPI (`editorial_workflow.py`). |

Recommend a follow-up ticket that either moves these out of `/api` or formally deletes them
once the backend equivalents are confirmed as the contract.

## Non-Goals

- Changing the backend logout endpoint or nginx.
- Fixing the separate latent `useAuth.logout()` POST-not-clearing-cookie baseline
  (AE-0165) — that path intentionally stays on the backend endpoint.
- Deleting the other three `app/api` routes (follow-up above).
- Cutover/hide/unpublish operations or any production write.

## Acceptance Criteria

- [x] AC1: a 401 redirects the browser to `/auth/logout?redirect=<path+query>`; the target
  is not under `/api/`.
- [x] AC2: GET `/auth/logout` clears `access_token`, best-effort POSTs `/api/auth/logout`
  and redirects to `/login?redirect=<safe>&error=session_expired`.
- [x] AC3: `redirect=//evil.com` and `redirect=https://evil.com` fall back to
  `/dashboard/chat` (no open redirect).
- [x] AC4: without a `redirect` param the login URL carries only `error=session_expired`.
- [x] AC5: a failing backend logout still clears the cookie and redirects.
- [x] AC6: middleware treats `/auth/logout` as public (no token required).
- [x] AC7: `src/app/api/auth/logout/route.ts` is gone and the URL inventory is regenerated.
- [x] AC8: the Gherkin file exists and each scenario is referenced by a test.
- [x] AC9: frontend gates are green (see Test Evidence).

## Gherkin Scenarios

```gherkin
Feature: An expired session logs out through a front-end route (AE-0429)

  Scenario: A 401 redirects to the front-end logout route
    Given the API answers 401 on a dashboard request
    When the API client handles the response
    Then the browser navigates to "/auth/logout?redirect=<path+query>"
    And the redirect target is not under "/api/"

  Scenario: The logout handler clears the session and returns to login
    Given a request to "/auth/logout?redirect=/dashboard/create/abc?step=content"
    When the logout handler runs
    Then the access_token cookie is cleared
    And the backend logout POST is attempted best-effort
    And the browser is redirected to "/login?redirect=/dashboard/create/abc?step=content&error=session_expired"

  Scenario: An external redirect is dropped
    Given a request to "/auth/logout?redirect=//evil.com"
    When the logout handler runs
    Then the browser is redirected to "/login?redirect=/dashboard/chat&error=session_expired"

  Scenario: A request without a redirect param still reaches login
    Given a request to "/auth/logout"
    When the logout handler runs
    Then the browser is redirected to "/login?error=session_expired"

  Scenario: A failing backend logout still ends the front-end session
    Given the backend logout POST fails
    When the logout handler runs
    Then the access_token cookie is cleared
    And the browser is redirected to "/login?error=session_expired"

  Scenario: The logout route is reachable without a token
    Given an unauthenticated request to "/auth/logout"
    When the middleware classifies the path
    Then the route is public and is not redirected to login
```

Full scenarios: `frontend/tests/features/session-expired-redirect-ae0429.feature`.

## Delta

### ADDED

- `frontend/src/app/auth/logout/route.ts` (moved from `app/api/auth/logout/route.ts`).
- `frontend/src/app/auth/logout/route.test.ts`.
- `frontend/tests/features/session-expired-redirect-ae0429.feature`.
- `PUBLIC_ROUTE_PATHS.LOGOUT`.
- `.agent/tasks/AE-0429-…md`, `.agent/reports/AE-0429.dev-summary.md`.

### MODIFIED

- `frontend/src/lib/api-client.ts` (401 redirect uses `PUBLIC_ROUTE_PATHS.LOGOUT`).
- `frontend/src/modules/identity/guards.ts` (`/auth/logout` is public).
- Tests: `api-client.test.ts`, `middleware.test.ts`.
- `frontend/scripts/url-inventory.snapshot.json` (regenerated).
- `frontend/tests/e2e/auth-baseline.spec.ts` (stale comment only; behaviour unchanged).

### REMOVED

- `frontend/src/app/api/auth/logout/route.ts` (shadowed by nginx in prod).

## Affected Areas

- Backend: none.
- Frontend: auth redirect + route handler + route guards.
- Database: none.
- API: front-end route moves `/api/auth/logout` (GET) → `/auth/logout` (GET). The backend
  `POST /api/auth/logout` is unchanged.
- Tests: route handler, api-client, middleware guard, Gherkin.
- Docs: ticket + dev summary.
- Prompts/LLM: none.
- Observability: none.
- Deployment: no nginx change needed; the new path is served by the Next frontend.

## Dependencies

- Blocks: none.
- Blocked by: none.
- Related: AE-0165 (latent logout baseline), AE-0164 (route guards).

## Implementation Plan

1. Add the `LOGOUT` path constant; repoint the 401 redirect.
2. `git mv` the handler out of `/api`; keep behaviour identical.
3. Mark the path public in the identity guards.
4. Delete the shadowed route; regenerate the URL inventory.
5. Write the `.feature`, then the tests, then run the gates.

## QA Checklist

- [x] Security reviewed (open-redirect sanitization covered; cookie cleared on Next response)
- [x] Code quality reviewed (typecheck + lint green)
- [x] Acceptance criteria validated
- [x] Edge cases tested (external redirects, no param, backend failure, no token)
- [x] Orphan/unfinished code checked (shadowed route deleted; follow-up documented)

## Progress Log

### 2026-10-19

Ticket created from the orchestrator brief and the verified prod root cause. Handler moved
to `/auth/logout`, 401 redirect repointed, guards/tests/feature added, URL inventory
regenerated.

## Files Touched

- `frontend/src/app/auth/logout/route.ts` (moved) + `route.test.ts`
- `frontend/src/app/api/auth/logout/route.ts` (deleted)
- `frontend/src/constants/public-routes.ts`
- `frontend/src/lib/api-client.ts` + test
- `frontend/src/modules/identity/guards.ts`
- `frontend/src/constants/middleware.test.ts`
- `frontend/tests/features/session-expired-redirect-ae0429.feature`
- `frontend/tests/e2e/auth-baseline.spec.ts` (comment)
- `frontend/scripts/url-inventory.snapshot.json`

## Test Evidence

Commit `9d9c44ac8`. Full frontend gate set reproduced locally via
`bash scripts/ci/gate-capture.sh frontend:<gate>`; mutation deferred to CI per the worker
memory policy.

- Targeted: `npx vitest run src/app/auth/logout/route.test.ts src/lib/api-client.test.ts
  src/constants/middleware.test.ts` → 3 files / 64 tests passed.
- Full suite: 182 files / 1538 tests passed.
- Build route list contains `ƒ /auth/logout` and no `ƒ /api/auth/logout`.

GATES_JSON: {"pass":16,"fail":0,"skip":1,"results":[{"gate":"frontend:lint","status":"PASS"},{"gate":"frontend:lint-changed","status":"PASS"},{"gate":"frontend:component-types","status":"PASS"},{"gate":"frontend:duplication","status":"PASS"},{"gate":"frontend:dead-code","status":"PASS"},{"gate":"frontend:typecheck","status":"PASS"},{"gate":"frontend:build","status":"PASS"},{"gate":"frontend:legacy-guard","status":"PASS"},{"gate":"frontend:legacy-inventory","status":"PASS"},{"gate":"frontend:format","status":"PASS"},{"gate":"frontend:security","status":"PASS"},{"gate":"frontend:integrity","status":"PASS"},{"gate":"frontend:test","status":"PASS"},{"gate":"frontend:schema-drift","status":"PASS"},{"gate":"frontend:duplication-tests","status":"PASS"},{"gate":"frontend:dead-files","status":"PASS"},{"gate":"frontend:mutation","status":"SKIP"}]}

See `.agent/reports/AE-0429.dev-summary.md`.

## QA Report

Pending external QA.

## Decision Log

- **Move out of `/api` instead of adding an nginx exception**: the proxy rule is what keeps
  the Next route from ever running; a front-end path (`/auth/logout`) is immune to it and
  needs no deployment change. Keeping `API_ENDPOINTS.AUTH_LOGOUT` for the backend POST
  avoids touching the logout mutation.
- **Do not delete the other three shadowed routes here**: they currently resolve to
  same-path FastAPI endpoints, so there is no user-visible bug; listed as a follow-up with
  prod-serving evidence instead.

## Blockers

None.

## Final Summary

Pending QA / merge.
