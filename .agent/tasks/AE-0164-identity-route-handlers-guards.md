# AE-0164 — Frontend: relocate auth route handlers + guards behind the identity contract

Status: Dev Complete
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

Second identity slice: route the auth route handlers (app/api/auth/*) + route-level guards (middleware.ts + admin/login guards) through the modules/identity public contract established in AE-0156, keeping App Router paths + auth behavior byte-identical.

## Problem

AE-0156 moves the auth/session CLIENT lib into modules/identity, but the route handlers under app/api/auth/* and the route-level guards (middleware, admin) are route-adjacent and higher-risk; they are split into this separate slice.

## Scope

Route app/api/auth/* handlers + middleware/admin guards through @/modules/identity (the contract from AE-0156); keep the route URLs + redirects + cookie/JWT behavior byte-identical; lean on the AE-0165 auth e2e. No behavior change.

## Non-Goals

- No App Router URL/route-handler path change; no auth behavior change.
- The shared HTTP client (authenticated-fetch/server-fetch) stays in lib/ as platform infra (NOT moved into identity).

## Modularization Alignment (2026-06-16)

Phase 8 of the modularization plan (§Phase 8 "Remove legacy layers and adapters"), after Phases 0-7 merged.
See `docs/plans/phase-8-legacy-removal.md`.

## Acceptance Criteria

- [x] app/api/auth/* + middleware/admin guards SHALL go through the @/modules/identity contract
- [x] App Router URLs, redirects, cookie/JWT behavior byte-identical; AE-0165 auth e2e green
- [x] typecheck + lint (boundary 0/0) + 822 unit tests + build + check:legacy green

## Gherkin Scenarios

Not applicable — behavior-preserving relocation; verified by the AE-0165 auth e2e + the green-gate safety net.

## Dependencies

- Blocks: —
- Blocked by: AE-0156
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

- NEW `frontend/src/modules/identity/guards.ts` — route-level auth guard surface moved from `constants/middleware.ts`: `ROLES`, `PUBLIC_ROUTES`, `COOKIE_ACCESS_TOKEN`, `STATIC_FILE_PATTERN`, and the route-class predicates (`isPublicRoute`, `isPublicChatRoute`, `isAuthRoute`, `isAdminRoute`, `isDashboardRoute`, `isLegacyEditorRoute`, `isEditorDashboardRoute`, `isEditorRoute`, `isStaticAsset`).
- `frontend/src/modules/identity/index.ts` — barrel now also exports the guard surface from `./guards` (`COOKIE_ACCESS_TOKEN` now sourced from guards, exported once).
- `frontend/src/modules/identity/lib/auth-cookie.ts` — imports `COOKIE_ACCESS_TOKEN` from the sibling `../guards` (relative, internal) instead of `@/constants/middleware`, breaking the would-be barrel↔shim cycle.
- `frontend/src/constants/middleware.ts` — now a thin re-export shim from `@/modules/identity` (canonical home is the identity guards).
- `frontend/src/middleware.ts` — imports the guard predicates + `ROLES` + `COOKIE_ACCESS_TOKEN` (plus `clearAccessTokenCookie`/`verifyAccessToken` from AE-0156) all from `@/modules/identity`; the whole auth surface now flows through the contract.

Note: `app/api/auth/token` + `app/api/auth/logout` + `app/login` route handlers were already routed through `@/modules/identity` in AE-0156; this slice completes the route-level **guard** side.

## Dropped (Phase 8 dead-code removal)
- `decodeJwtPayload` (the `@deprecated` middleware decoder) — superseded by `verifyAccessToken`/`decodeJwtPayloadUnsafe`, no remaining consumer and not referenced by `constants/middleware.test.ts`. Removed rather than carried into the module (it also held magic numbers that the `modules/**` no-magic-numbers rule flags).

## Test Evidence

- `npm run typecheck` — clean.
- `npm run lint` — clean: boundary OK (0/0/0 new), URL inventory OK (26), **circular OK (0 cycles / 328 modules)** — the cookie-name import was repointed to the sibling guards module to avoid a cycle, component-type-location OK (57/57).
- `npm run test` — 823 passed.
- `npm run check:legacy` — passed.
- `npm run build` — succeeded.
- `npm run test:e2e:auth` — **7 passed** (the AE-0165 baseline proves the middleware guards behave byte-identically after the relocation).
- `check-integrity.sh frontend` — PASS, 0 blockers / 0 warnings.

## QA Report

Pending (Phase 8 end-of-phase QA on the full branch).

## Decision Log

- **Cycle avoidance:** `identity/lib/auth-cookie` sources `COOKIE_ACCESS_TOKEN` from the sibling `../guards` (not via the `@/constants/middleware` shim, which now points back at the barrel) so the barrel never imports a module that imports the barrel. `lint:circular` confirms 0 cycles.
- **Single COOKIE_ACCESS_TOKEN export:** the barrel exports it once, from `./guards` (removed from the auth-cookie export line) to avoid a duplicate-export conflict.
- **Dropped deprecated `decodeJwtPayload`** (see above) — in-scope Phase 8 legacy removal; behavior-preserving (unused).
- **Redirect helpers stay in middleware.ts:** `loginRedirectUrl`/`redirectWithClearedSession` are middleware-orchestration specific; they consume the identity contract (predicates + `clearAccessTokenCookie`) rather than being relocated, keeping the slice tight and risk low.

## Blockers

None.

## Final Summary

Completed identity SLICE 2: the route-level auth guard surface (role constants + route-class predicates + access-token cookie name + static-asset matcher) now lives in `modules/identity/guards.ts` behind the public barrel, with a re-export shim at `@/constants/middleware` and `middleware.ts` consuming the whole auth contract through `@/modules/identity`. Dropped the dead deprecated `decodeJwtPayload`. Byte-identical guard behavior: AE-0165 auth e2e 7/7 + 823 unit tests + boundary 0 + circular 0 + component-types 57/57 + build + check:legacy all green. `modules/identity` is now the single home of the frontend auth/session + route-guard contract.
