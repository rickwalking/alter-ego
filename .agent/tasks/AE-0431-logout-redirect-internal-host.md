# AE-0431 — /auth/logout redirects to https://0.0.0.0:3000/login

Status: Dev Complete
Tier: T1
Priority: P1
Type: Bug
Area: Frontend
Owner: worker (orchestrator-found prod bug, 2026-10-19)
Agent Lane: developer → qa → release
Branch: feat/ae-0431-logout-redirect-internal-host
Kanban Card: TBD
Created: 2026-10-19
Updated: 2026-10-19

## Goal

When a session expires, the browser always lands on the public login page
(`https://<public-host>/login?redirect=<safe>&error=session_expired`) — never on an
unreachable internal host like `https://0.0.0.0:3000/login`.

## Problem

Found by the orchestrator right after AE-0429 (#150) deployed (2026-10-19): a prod

```
GET https://marinssolutions.com/auth/logout?redirect=%2Fdashboard%2Fcreate%2F...
```

answers `307` with

```
Location: https://0.0.0.0:3000/login?redirect=...&error=session_expired
```

Browsers cannot reach `0.0.0.0:3000`, so an expired session still ends on a broken
page. The open-redirect protection works (`//evil.com` → `/dashboard/chat`).

Root cause (verified against prod evidence and `node_modules/next`):

- `frontend/src/app/auth/logout/route.ts:19` builds
  `new URL(PUBLIC_ROUTE_PATHS.LOGIN, request.url)`.
- Under the Next standalone server, `request.url` is the server's `initURL`
  (`next-server.js` `attachRequestMeta`): when `fetchHostname` + `port` are set (the
  standalone `server.js` binds `0.0.0.0:3000`), the URL is
  `https://0.0.0.0:3000<path>` — the **bind address**, not the public host. The
  `https` scheme comes from the forwarded `X-Forwarded-Proto`; the host does not.
- The middleware (`frontend/src/middleware.ts:22`) uses the same pattern but works in
  prod, because middleware receives the proxied Host. nginx sends `Host $host` and
  `X-Forwarded-Proto $real_scheme` for the frontend location
  (`nginx/nginx.conf.ssl:95-110`).
- `NextResponse.redirect` in Next 16.4 (`validateURL`) rejects relative URLs, so the
  fix must build an absolute URL whose host is **not** taken from `request.url`.

## Scope

1. Build the login URL in the logout handler from the proxy headers: host from
   `Host`, scheme from the first `X-Forwarded-Proto` value (restricted to
   `http`/`https`), falling back to `request.nextUrl` when a header is missing
   (local dev / direct requests — today's behaviour).
2. Keep `sanitizeLoginRedirect`, `error=session_expired`, the best-effort backend
   POST and the cookie clearing exactly as they are.
3. Grep-check the other Route Handlers that redirect with `request.url`
   (`NextResponse.redirect(` under `frontend/src/app/**/route.ts`) — the logout
   route is the only one (verified); middleware is left as is (it works in prod).
4. Gherkin: extend `frontend/tests/features/session-expired-redirect-ae0429.feature`
   with the internal-host scenario (same feature, same route).
5. Tests: a unit test where `request.url` is `http://0.0.0.0:3000/auth/logout?...`
   with `Host: marinssolutions.com` + `X-Forwarded-Proto: https` asserts the
   `Location` is `https://marinssolutions.com/login?...` and never contains
   `0.0.0.0`/`localhost`; keep all open-redirect and existing tests.

## Non-Goals

- No nginx, backend or middleware change.
- No `trustHostHeader` global Next config flip (app-wide blast radius).
- No prod writes; no deploy; no merge.

## Acceptance Criteria

- [x] AC1: with `request.url` on an internal bind address and forwarded
  `Host`/`X-Forwarded-Proto` headers, the logout `Location` uses the public host and
  https — it never contains `0.0.0.0` or `localhost`.
- [x] AC2: without forwarded headers the redirect still works (falls back to the
  request origin) — no regression for local/dev and the existing test matrix.
- [x] AC3: `sanitizeLoginRedirect`, `error=session_expired`, cookie clearing and the
  best-effort backend POST are unchanged (existing tests keep passing).
- [x] AC4: the Gherkin file documents the internal-host scenario and a test
  references it.
- [x] AC5: frontend gates are green (see Test Evidence).

## Gherkin Scenarios

Extends `frontend/tests/features/session-expired-redirect-ae0429.feature`:

```gherkin
  Scenario: The login Location never exposes the internal server host
    Given a request to "/auth/logout?redirect=/dashboard/create/abc?step=content"
      whose URL host is the standalone server bind address "0.0.0.0:3000"
      with headers "Host: marinssolutions.com" and "X-Forwarded-Proto: https"
    When the logout handler runs
    Then the access_token cookie is cleared
    And the browser is redirected to "https://marinssolutions.com/login?redirect=/dashboard/create/abc?step=content&error=session_expired"
    And the Location header does not contain "0.0.0.0" or "localhost"
```

## Affected Areas

- [x] Frontend: `src/app/auth/logout/route.ts`, `src/constants/auth.ts`,
  `src/modules/identity/lib/auth-cookie.ts` (reuses the header constant)
- [ ] Backend: none
- [x] Tests: `src/app/auth/logout/route.test.ts`,
  `frontend/tests/features/session-expired-redirect-ae0429.feature`
- Database: none
- API: none (same route, same contract)
- Docs: ticket + dev summary
- Prompts/LLM: none
- Observability: none
- Deployment: normal frontend build; no infra change

## Dependencies

- Blocks: none.
- Blocked by: none.
- Related: AE-0429 (the route this fixes), AE-0165 (latent logout baseline).

## Progress Log

### 2026-10-19

Ticket created from the orchestrator brief (root cause verified on prod). Fix
implemented in the logout handler, spec + tests added, gates reproduced locally.

## Files Touched

- `frontend/src/app/auth/logout/route.ts`
- `frontend/src/constants/auth.ts`
- `frontend/src/modules/identity/lib/auth-cookie.ts`
- `frontend/src/app/auth/logout/route.test.ts`
- `frontend/tests/features/session-expired-redirect-ae0429.feature`
- `.agent/tasks/AE-0431-logout-redirect-internal-host.md`
- `.agent/reports/AE-0431.dev-summary.md`

## Test Evidence

Full frontend gate set reproduced locally via `bash scripts/ci/gate-capture.sh
frontend` (never piped; wrapper exit = gate exit).

GATES_JSON: {"pass":17,"fail":0,"skip":0,"results":[{"gate":"frontend:lint","status":"PASS"},{"gate":"frontend:lint-changed","status":"PASS"},{"gate":"frontend:component-types","status":"PASS"},{"gate":"frontend:duplication","status":"PASS"},{"gate":"frontend:dead-code","status":"PASS"},{"gate":"frontend:typecheck","status":"PASS"},{"gate":"frontend:build","status":"PASS"},{"gate":"frontend:legacy-guard","status":"PASS"},{"gate":"frontend:legacy-inventory","status":"PASS"},{"gate":"frontend:format","status":"PASS"},{"gate":"frontend:security","status":"PASS"},{"gate":"frontend:integrity","status":"PASS"},{"gate":"frontend:test","status":"PASS"},{"gate":"frontend:schema-drift","status":"PASS"},{"gate":"frontend:duplication-tests","status":"PASS"},{"gate":"frontend:dead-files","status":"PASS"},{"gate":"frontend:mutation","status":"PASS"}]}

Targeted: `npx vitest run src/app/auth/logout/route.test.ts src/lib/auth-cookie.test.ts`
→ 2 files / 12 tests passed. Full details in `.agent/reports/AE-0431.dev-summary.md`.

## QA Report

Pending external QA.

## Decision Log

- **Headers over `trustHostHeader`**: a one-route fix with the same trust model as
  the working middleware, instead of flipping a Next config that changes
  `request.url` for every route, middleware and API handler.
- **Host from the `Host` header (nginx `$host`), not `X-Forwarded-Host`**: the
  frontend location does not forward `X-Forwarded-Host`; `Host` is always set.
  Client-controllable, but the redirect only ever points at the host the user
  already addressed — same exposure as middleware today; the `redirect` param
  itself stays path-sanitized.
- **Scheme restricted to `http`/`https`**: the header value is parsed defensively
  so a malformed proto cannot produce a non-http Location.

## Blockers

None.
