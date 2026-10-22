# AE-0481 — Login form leaks credentials into the URL when submitted before hydration

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Frontend
Owner: Worker (Claude) — AE-0481 shepherd, dashboard QA DQ-B-07
Branch: fix/ae-0481-login-form-post
Created: 2026-10-22
Updated: 2026-10-22

## Goal

Credentials can never reach a URL: a login submitted before hydration, or with JavaScript off, posts them.

## Problem

Dashboard QA (DQ-B-07): the server-rendered login `<form>` had no `method`/`action`, so a submit before React
hydrated did the browser default, a GET to `/login?email=…&password=…`. The password then sits in the address bar,
the history and every proxy/CDN access log.

## Scope

- `LoginForm` renders `method="post" action="/auth/login"`; hydrated, `handleSubmit` still takes over (JSON fetch).
- New route handler `POST /auth/login` (outside `/api`, which nginx sends to FastAPI): accepts only this site's own
  post (login CSRF): `Sec-Fetch-Site` must be `same-origin`/`none`, or without Fetch Metadata a real `Origin` naming
  the host; the site-wide `no-referrer` policy makes browsers send `Origin: null` and no `Referer` here. It signs in
  through the backend, sets the session cookie and 303s to the default landing page (the return path is not
  visible to it); any failure 303s to `/login?error=invalid_credentials` (an error code only, never the fields).
- The login page shows "Invalid email or password" for `?error=invalid_credentials`, and "Too many sign-in attempts"
  for `?error=too_many_attempts` (backend 429 on the no-JS path; the hydrated form maps a 429 the same way).
- Session cookie parity (#231 review): the shared `setAccessTokenCookie` sets `SameSite=Strict` and `Max-Age` from
  `ACCESS_TOKEN_EXPIRE_MINUTES` (the backend's setting, default 60), like FastAPI's login cookie; both prod compose
  services read the same `ACCESS_TOKEN_EXPIRE_MINUTES` (default 60). The unused-in-prod `api/auth/token` BFF shares it.
- nginx (`nginx.conf`, `nginx.conf.ssl`): `location = /auth/login` with `limit_req zone=api burst=5 nodelay`, because
  the backend's login limit only sees the frontend container's IP.
- Other password forms: the admin create-user dialog (its password field) is a POST form too; it only mounts after
  a click, so it is never server-rendered. The change-password dialog has no password input (it resets).

## Non-Goals

- Changing the JavaScript sign-in flow.

## Acceptance Criteria

- [x] The server-rendered login form is `method="post"` to `/auth/login`.
- [x] A no-JavaScript sign-in signs in by POST; a failed one returns to login with an error code only.
- [x] A cross-site post to `/auth/login` is refused (403) without calling the backend.
- [x] Every form with a password field is a POST form (source scan fires on a seeded GET-default form).
- [x] Browser check: a JavaScript-disabled submit never navigates to a URL containing the credentials.
- [x] The no-JS session cookie is HttpOnly, SameSite=Strict, with the backend's token lifetime.
- [x] nginx rate-limits `/auth/login` per client IP; a backend 429 shows "too many attempts".

## Repro Steps

1. Open `/login` with JavaScript disabled (or click Sign in before hydration). Before: the URL becomes
   `/login?email=…&password=…`. After: `POST /auth/login`, then `/login?error=invalid_credentials` or the dashboard.

## Affected Areas

- [x] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-22

Fix + tests. Verified against a local dev server: SSR form tag `action="/auth/login" method="post"`; a no-JS POST
answers 303 to `/login?error=invalid_credentials&redirect=%2Fdashboard%2Fknowledge` (no backend running); a
cross-site POST answers 403. Playwright cannot run locally (no chromium build for Ubuntu 26.04); the e2e check runs
in CI's auth-baseline job.

First CI run: the e2e post got 403. The browser sent `Origin: null` + `Sec-Fetch-Site: same-origin` (the root
metadata sets `referrer: "no-referrer"`), which the first Origin check treated as cross-site, and no `Referer`, so a
Referer-based return path could never work. Fetch Metadata now decides; the return path was dropped.

## Files Touched

- frontend/src/app/login/login-form.tsx, use-login.ts
- frontend/src/app/auth/login/route.ts (+ route.test.ts, new)
- frontend/src/components/admin/create-user-dialog.tsx
- frontend/src/constants/auth.ts
- frontend/src/app/login/login-form-post.test.tsx, frontend/src/scripts/password-forms-post.test.ts (new)
- frontend/tests/e2e/auth-baseline.spec.ts
- frontend/tests/features/login-form-post-only.feature (new)
- frontend/src/modules/identity/lib/auth-cookie.ts (+ src/lib/auth-cookie.test.ts), src/app/login/use-login.test.ts (new)
- frontend/src/scripts/nginx-login-limit.test.ts (new), frontend/src/i18n/locales/en.json, pt.json
- nginx/nginx.conf, nginx/nginx.conf.ssl, docker-compose.prod.yml

## Test Evidence

See PR. Mutation: CI only.

## QA Report

Pending (CI on the PR head).

## Blockers

None.
