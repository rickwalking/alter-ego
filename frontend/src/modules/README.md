# `modules/` — bounded-context layer (public-contract convention)

Phase 7 reorganizes `src/features/**` into **bounded-context modules** that share
the backend domain glossary (`docs/architecture/domain-glossary.md`: `knowledge`,
`identity`, `conversation`, `editorial`, `editorial-operations`,
`carousel-presentation`, `persona`, `quality`, `publishing`).

**Status: Phase 7 complete (AE-0142 exit gate).** All eight feature-backed
contexts have been migrated into this layer behind public contracts —
`publishing` (AE-0137), `editorial` + `editorial-operations` (AE-0138),
`carousel-presentation` + `persona` + `quality` + `conversation` + `knowledge`
(AE-0139) — and business components were re-homed out of the global atomic
folders (AE-0140). The cross-context boundary count has been ratcheted from the
Phase-7-start baseline of 23 down to **0**. `identity` remains a documented
deferral (see below). `_example/` is a retained non-feature anchor for the
boundary checker. Legacy `@/features/*` paths still resolve via thin re-export
shims; their removal (and exhaustive component re-homing, route-page thinning,
and frontend `identity` consolidation) is a consent-gated **Phase 8** follow-up
(ticket AE-0143).

## The convention

1. Each bounded context lives at `src/modules/<context>/`.
2. A context exposes **only** its public contract — the barrel
   `src/modules/<context>/index.ts`. Everything else under the module is an
   internal implementation detail.
3. **Cross-module and `app/` imports MUST target the barrel**
   (`@/modules/<context>`), **never** a deep internal path
   (`@/modules/<context>/<internal>`).
4. A module may freely import its own internals (`@/modules/<self>/...`) and the
   shared layers (`@/components`, `@/lib`, `@/constants`, `@/i18n`, `@/schemas`).

```ts
// ✅ allowed — public contract
import { PublishingPanel } from "@/modules/publishing";

// ❌ forbidden — reaches past the public contract into an internal
import { PublishingPanel } from "@/modules/publishing/components/publishing-panel";
```

## Enforcement

`scripts/check-feature-boundaries.mjs` (run via `npm run lint:boundaries`, part
of `npm run lint`) enforces this. During the migration window it scans BOTH
layers and treats `app/` as a consumer:

| Layer            | Owner attribution            | Rule                                                                            |
| ---------------- | ---------------------------- | ------------------------------------------------------------------------------- |
| `src/features/X` | `@/features/X`               | a feature must not import another feature's internals (legacy ratchet, AE-0083) |
| `src/modules/X`  | `@/modules/X`                | a module must not import another module's **internal** (`@/modules/Y/<deep>`)   |
| `src/app`        | consumer (no owning context) | may import a module's **public contract** only — never `@/modules/Y/<deep>`     |

The ratchet is **down-only**: the grandfathered cross-boundary count
(`scripts/feature-boundary-baseline.json`) may stay equal or shrink, never grow.
Module-internal and `app/`→module-internal imports are NOT grandfathered — they
fail immediately (there are none today, and none should ever be added).

Regenerate the baseline (only ever to ratchet DOWN) with
`npm run boundaries:baseline`.

## Identity context — deferred to Phase 8 (AE-0139)

The glossary lists an `identity` bounded context, but there is **no
`features/auth`** to migrate: frontend auth/session lives in `lib/` (the
authenticated fetch / session helpers) and `app/` (route-level guards and
sign-in pages), both of which are route-adjacent and risky to relocate in a
behavior-preserving pass. AE-0139 therefore makes identity a **docs-only**
note: no `modules/identity/` is created and no code moves. Frontend identity
consolidation into a dedicated module is **deferred to Phase 8**.
