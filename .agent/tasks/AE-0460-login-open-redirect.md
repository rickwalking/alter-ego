# AE-0460 — Open redirect after login via `redirect=/\host`

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Frontend
Owner: Worker (Claude) — AE-0453 site scan, SITE-01
Branch: fix/ae-0460-login-open-redirect
Created: 2026-10-22
Updated: 2026-10-22

## Goal

A login link can only ever return the signed-in user to a page on this site.

## Problem

Found by the AE-0453 site scan (SITE-01, High). On prod, signing in through
`/login?redirect=%2F%5Cexample.org` (`/\example.org`) lands on `https://example.org/`.
`sanitizeLoginRedirect` rejected only a leading `//`; browsers (WHATWG URL) read `\` as `/`, so `/\host`
is scheme-relative. A real marinssolutions.com login link could forward a fresh session to a phishing page.
`https://…` and `//…` were already rejected.

## Scope

- `sanitizeLoginRedirect` (moved to `modules/identity/lib/login-redirect.ts`) parses the value against a
  placeholder origin and keeps it only when it is same-origin and every percent-decoding (3 rounds) starts with a
  single `/` and contains no backslash or control character; malformed encodings and the login page are rejected.
  The normalised path + query + hash is returned.
- Consumers checked: login page (`router.push`), `/auth/logout` (re-sanitises the param it forwards), middleware
  (sets the param from `request.nextUrl.pathname` only), api-client 401 handler (builds it from `location`). Backend
  has no redirect/next/returnTo parameter.

## Non-Goals

- No change to which pages need a session.

## Acceptance Criteria

- [x] `/\host`, `/%5Chost`, `/%255Chost`, `\\host`, tab/newline/NUL variants, `/%2F%2Fhost`, absolute,
      scheme-relative and `javascript:`/`data:` values fall back to `/dashboard/chat`.
- [x] Same-origin paths keep their query and hash (`/dashboard/calendar?view=month#today`, `/blog?q=agent%20loops`).
- [x] A return path to `/login` (also via `/dashboard/../login`) falls back.
- [x] `/auth/logout?redirect=/\host` forwards `redirect=/dashboard/chat`.

## Repro Steps

1. Logged out, open `https://marinssolutions.com/login?redirect=%2F%5Cexample.org`.
2. Sign in. Before: browser at `https://example.org/`. After: `/dashboard/chat`.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-22 01:30

Reproduced on prod (`scripts/redirect.js` in the AE-0453 QA run), failing table-driven tests first (15/36 red),
fix, logout route cases added.

## Files Touched

- frontend/src/modules/identity/lib/login-redirect.ts (new)
- frontend/src/modules/identity/lib/login-redirect.test.ts (new)
- frontend/src/modules/identity/lib/auth-cookie.ts
- frontend/src/modules/identity/index.ts
- frontend/src/constants/auth.ts
- frontend/src/app/auth/logout/route.test.ts
- frontend/tests/features/login-redirect-ae0460.feature (new)

## Test Evidence

Local, individual non-mutation frontend gates: lint, typecheck, gherkin-refs, format, security, integrity,
dead-code, duplication, duplication-tests, dead-files, legacy-guard, component-types, schema-drift, test
(2041 passed), build — all PASS. Mutation: CI only (AE-0448).

## QA Report

Pending (CI on the PR head).

## Blockers

None.
