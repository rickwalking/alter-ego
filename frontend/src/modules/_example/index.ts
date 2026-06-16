/**
 * `_example` — public-contract anchor for the modules/ layer (AE-0136).
 *
 * This is NOT a real bounded context. It exists only so the boundary checker
 * has a concrete `modules/<context>/index.ts` barrel to scan during the
 * Phase 7 migration window, before any real feature is moved (later tickets:
 * AE-0137..AE-0139). It exports nothing and is not imported by the app.
 *
 * The convention it demonstrates: every module exposes ONLY its public
 * contract via this `index.ts` barrel. Cross-module / app imports MUST target
 * `@/modules/<context>` (this file), never `@/modules/<context>/<internal>`.
 *
 * See `src/modules/README.md` for the full convention.
 */

export {};
