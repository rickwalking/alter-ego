# AE-0165 — Frontend: auth e2e safety net (login/logout/refresh/guard) — precondition for identity

Status: Review
Tier: T2
Priority: High
Type: Task
Area: Frontend/Tests
Owner: developer
Agent Lane: planner → architect → developer → qa → release
Branch: feat/phase-8-legacy-removal
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Add a Playwright auth e2e safety net (login, logout, token refresh, protected-route guard/redirect) BEFORE the identity module relocation, so the otherwise-unverifiable 'byte-identical auth behavior' of AE-0156/0164 is provable.

## Problem

AE-0156 (identity module) relocates auth/session code with 35+ importers across middleware, route handlers, and pages, but the repo has only tests/e2e/auth.setup.ts (no login/logout/refresh/guard e2e). Without a behavior net, the identity relocation can't be proven safe.

## Scope

Author Playwright e2e specs covering: successful login -> authenticated session; logout -> session cleared + redirect; expired/refresh token flow; unauthenticated access to a protected route -> redirect to login; admin-guard behavior. Test the EXISTING behavior (this is the baseline). No app code change.

## Non-Goals

- No app/auth behavior change (tests only — capture current behavior as the baseline).
- Not the identity relocation itself (that is AE-0156/0164).

## Modularization Alignment (2026-06-16)

Phase 8 of the modularization plan (§Phase 8 "Remove legacy layers and adapters"), after Phases 0-7 merged.
See `docs/plans/phase-8-legacy-removal.md`.

## Acceptance Criteria

- [x] Playwright e2e SHALL cover login, logout, token refresh, protected-route guard/redirect, and admin guard against current behavior
- [x] The e2e suite SHALL pass on the current code (the auth baseline)
- [x] Wired into CI (or the e2e job) so AE-0156/0164 can prove byte-identical auth behavior

## Gherkin Scenarios

Given a valid user, When they log in, Then a session is established and protected routes load. Given a logged-in user, When they log out, Then the session is cleared and they are redirected to login. Given no session, When a protected route is requested, Then the user is redirected to login. (Captured as the pre-relocation baseline.)

## Dependencies

- Blocks: AE-0156
- Blocked by: —
- Related: AE-0152

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-16

Ticket created by planner (Phase 8 architect-validation round-1 fix).

## Files Touched

- NEW `frontend/tests/e2e/auth-baseline.spec.ts` — 7 backend-free baseline scenarios (see below).
- NEW `frontend/tests/e2e/helpers/auth-baseline-tokens.ts` — crafts unsigned `header.payload.sig` JWTs (admin/editor/viewer/expired) + `accessTokenCookie()` helper (localhost, path `/`, httpOnly, SameSite=Lax).
- `frontend/playwright.config.ts` — added a dedicated `auth-baseline` project (no `storageState`, no `dependencies: ['setup']`) and excluded `auth-baseline.spec.ts` from the existing `chromium` project's `testIgnore` so it never triggers the real-backend admin login.
- `frontend/package.json` — added `"test:e2e:auth": "playwright test --project=auth-baseline"`.
- `.github/workflows/frontend-quality-gates.yml` — added the blocking `e2e-auth-baseline` job (npm ci → `playwright install --with-deps chromium` → `npm run test:e2e:auth`; webServer auto-starts `npm run dev`; no backend/keys).

TEST/CONFIG/CI ONLY — no `src/` (app) code changed.

## Test Evidence

- `npx playwright test --project=auth-baseline` — **7 passed** (deterministic; re-run confirmed, no flake).
- `npm run typecheck` — clean. `npm run lint` — clean (eslint --quiet + boundaries 0 + url 26 + circular 0 + component-types 57/57).
- `check-integrity.sh frontend` — PASS, 0 blockers / 0 warnings.

Scenarios (assert ACTUAL current behavior):
1. Unauthenticated → protected route redirects to `/login?redirect=<path>`.
2. Login success → `POST /api/auth/token` mocked + cookie set → navigates to `/dashboard/chat`.
3. Logout (see Decision Log — captures the real bounce-back behavior).
4. Expired token on protected route → `/login?redirect=...` + `access_token` cookie cleared.
5. Editor role on `/admin/users` → `/403`.
6. Admin role on `/admin/users` → loads (no `/403`).
7. Plain (viewer) role on editor-only dashboard route → `/403`.

## QA Report

Pending (Phase 8 end-of-phase QA on the full branch).

## Decision Log

- **Backend-free determinism:** the frontend runtime has no `AUTH_JWT_SECRET`/`SECRET_KEY`, so `verifyAccessToken` uses the `decodeJwtPayloadUnsafe` fallback (signature ignored). The specs therefore craft unsigned tokens + set the `access_token` cookie via `context.addCookies`, and mock `/api/auth/*` + `/api/admin/*` via `page.route`. No live backend or external keys.
- **LATENT LOGOUT BUG captured as baseline (NOT fixed):** `useAuth.logout()` calls `fetch POST /api/auth/logout`, but `app/api/auth/logout/route.ts` only defines **GET** (GET is what clears the cookie). So the POST does not clear `access_token`; `window.location.href="/login"` then navigates with a still-valid cookie, and middleware (auth route + valid token) bounces it back to `/dashboard/chat`. The test pins this real behavior (cookie still present, final URL `/dashboard/chat`). Flagged for a follow-up fix; out of scope for this baseline ticket.
- **Pre-existing i18n gap noted:** `/admin/users` logs `MISSING_MESSAGE: Could not resolve 'admin'` at runtime but still renders; pre-existing app behavior, not introduced here, and the test tolerates it.

## Blockers

None.

## Final Summary

Added a deterministic, backend-free Playwright auth baseline (7 scenarios covering login, logout, expiry/refresh, unauthenticated guard, admin guard, editor-dashboard guard) in a dedicated `auth-baseline` project + a blocking CI job, pinning the CURRENT frontend auth behavior so the AE-0156/0164 identity relocation can be proven byte-identical. Test/config/CI only; no app code changed. Surfaced (and faithfully captured, not fixed) a latent logout cookie-clearing bug for follow-up.
