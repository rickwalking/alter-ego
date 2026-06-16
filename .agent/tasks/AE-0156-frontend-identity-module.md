# AE-0156 — Frontend: modules/identity — consolidate auth/session behind a public contract

Status: Review
Tier: T2
Priority: High
Type: Task
Area: Frontend
Owner: developer
Agent Lane: planner → architect → developer → qa → release
Branch: feat/phase-8-legacy-removal
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

SLICE 1 of identity (route handlers/guards are the separate AE-0164 slice): move the auth/session-SPECIFIC client lib (lib/jwt-auth, lib/auth-cookie, the auth client surface) into a modules/identity bounded context behind a public contract. CRITICAL SCOPE BOUND: lib/authenticated-fetch + lib/server-fetch are the APP-WIDE HTTP client (used by every module — not auth-specific) and STAY in lib/ as platform infra; they are NOT moved into identity.

## Problem

Phase 7 deferred identity because auth/session is route-adjacent (guards + sign-in pages) and risky to relocate behavior-preservingly. Architect validation (round 1) found the original single-ticket scope too large: the "auth" libs have 35+ importers across middleware/route handlers/most modules, and authenticated-fetch/server-fetch is the shared HTTP client (mis-classified as auth). Identity is therefore split: AE-0156 (this — auth-specific client lib) + AE-0164 (route handlers/guards), both gated on the AE-0165 auth e2e.

## Scope

Create modules/identity with a public barrel; move ONLY the auth-specific client logic (jwt-auth, auth-cookie, the login/session client surface) behind it; route consumers through @/modules/identity; leave re-export shims at the old lib/ auth paths so nothing breaks. The shared authenticated-fetch/server-fetch HTTP client STAYS in lib/. Verified byte-identical via the AE-0165 auth e2e + unit tests.

## Non-Goals

- No auth BEHAVIOR change (same tokens/cookies/guards/redirects).
- No App Router URL change; route handlers under app/api/auth + guards are AE-0164 (not this slice).
- authenticated-fetch / server-fetch (the app-wide HTTP client) are NOT moved (platform infra, not auth).

## Modularization Alignment (2026-06-16)

Phase 8 of the modularization plan (§Phase 8 "Remove legacy layers and adapters") — the final phase, after
Phases 0-7 merged (PRs #15-#21). Removes the temporary migration scaffolding to zero. Class A (safe cleanup) is
behavior-preserving and holds the existing green gates with down-only ratchets; Class B (auto-publish cutover +
destructive column drop) is consent-gated + drain-gated (ADR-0008). See `docs/plans/phase-8-legacy-removal.md`.

## Acceptance Criteria

- [x] modules/identity SHALL own the auth-SPECIFIC client lib (jwt-auth, auth-cookie, login/session client) behind a public contract; consumers import @/modules/identity; re-export shims keep old lib/ auth paths resolving
- [x] authenticated-fetch / server-fetch (app-wide HTTP client) SHALL remain in lib/ (NOT moved into identity)
- [x] Auth behavior byte-identical; the AE-0165 auth e2e SHALL pass; App Router URLs unchanged
- [x] typecheck + lint (boundary 0/0) + 822 unit tests + build + check:legacy green

## Gherkin Scenarios

Not applicable — legacy-removal cleanup; verified by the green-gate safety net (back-end gates.sh + check-integrity + arch-ratchet; front-end typecheck/lint/boundaries/url/circular/tests/build).

## Dependencies

- Blocks: AE-0164
- Blocked by: AE-0153, AE-0165
- Related: AE-0152

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-16

Ticket created by planner (Phase 8 breakdown).

## Files Touched

- NEW `frontend/src/modules/identity/` — `index.ts` (public barrel), `types.ts` (`AccessTokenPayload`, `AuthUser`, `UseAuthResult` extracted), `lib/jwt-auth.ts`, `lib/auth-cookie.ts`, `hooks/use-auth.ts` (moved implementations).
- Shims (re-export from `@/modules/identity`): `frontend/src/lib/jwt-auth.ts`, `frontend/src/lib/auth-cookie.ts`, `frontend/src/hooks/use-auth.ts`.
- Consumers repointed to the `@/modules/identity` barrel: `src/middleware.ts`, `src/app/login/page.tsx`, `src/app/api/auth/token/route.ts`, `src/app/api/auth/logout/route.ts`, `src/modules/publishing/blog/components/public-post/blog-post-admin-panel.tsx`, `src/modules/editorial/workflow/hooks/use-collaborative-edit.ts` (the two cross-module ones are boundary-required), `src/components/admin/admin-sidebar.tsx`, `src/components/organisms/neon-sidebar.tsx`, `src/components/layout/header.tsx`, `src/components/layout/mobile-nav.tsx`.
- Test `vi.mock` targets repointed (`@/hooks/use-auth` → `@/modules/identity`): `neon-sidebar.test.tsx`, `layout/header.test.tsx`, `blog-post-admin-panel.test.tsx`. The two lib unit tests stay on the old paths and now validate the shims.
- UNTOUCHED (by design): `src/lib/authenticated-fetch.ts`, `src/lib/server-fetch.ts` (app-wide HTTP client).

## Test Evidence

- `npm run typecheck` — clean.
- `npm run lint` — clean: boundary OK (0/0/0 new), URL inventory OK (26), circular OK (0 cycles / 327 modules), component-type-location OK (57/57, 0 new).
- `npm run test` — 823 passed.
- `npm run check:legacy` — passed.
- `npm run build` — succeeded.
- `npm run test:e2e:auth` — **7 passed** (the AE-0165 baseline proves byte-identical auth behavior post-relocation).
- `check-integrity.sh frontend` — PASS, 0 blockers / 0 warnings.

## QA Report

Pending (Phase 8 end-of-phase QA on the full branch).

## Decision Log

- **Barrel-only cross-module imports:** the two cross-module hook consumers (publishing, editorial) and the `app/` consumers import the `@/modules/identity` barrel, never a deep internal — keeping the feature-boundary ratchet at 0.
- **Hook types extracted to `types.ts`:** moving `use-auth.ts` under `src/modules/**` subjects it to the component-type-location ratchet, so `AuthUser`/`UseAuthResult` (and `AccessTokenPayload`) were moved to a colocated `types.ts` (no new inline declarations).
- **Test mocks repointed:** components now import `useAuth` via the barrel, so the 3 `vi.mock("@/hooks/use-auth")` calls were repointed to `@/modules/identity` to keep intercepting (no tests weakened/skipped/deleted).
- **HTTP client stays in lib/:** `authenticated-fetch`/`server-fetch` are app-wide platform infra (used by most modules), not auth-specific — explicitly NOT moved (AE-0164/later does NOT move them either).

## Blockers

None.

## Final Summary

Created `modules/identity` (SLICE 1) owning the auth-SPECIFIC client lib — JWT verify/decode, the access-token cookie helpers, login-redirect sanitization, and the `useAuth` session hook — behind a public barrel, with re-export shims at the old `lib/`/`hooks/` paths and consumers routed through `@/modules/identity`. The app-wide HTTP client stays in `lib/`. Behavior is byte-identical: the AE-0165 auth e2e (7 specs) plus 823 unit tests, boundary 0, build, and check:legacy all pass. AE-0164 (route handlers/guards) is the next identity slice.
