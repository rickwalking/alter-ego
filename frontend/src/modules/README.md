# `modules/` — bounded-context layer (public-contract convention)

Phase 7 reorganizes `src/features/**` into **bounded-context modules** that share
the backend domain glossary (`docs/architecture/domain-glossary.md`: `knowledge`,
`identity`, `conversation`, `editorial`, `editorial-operations`,
`carousel-presentation`, `persona`, `quality`, `publishing`).

This directory is the target layer. **AE-0136 only scaffolds it** — no real
feature has been moved yet. `_example/` is a non-feature anchor that gives the
boundary checker a concrete `modules/<context>/index.ts` barrel to scan during
the migration window; later tickets (AE-0137…AE-0139) migrate features in.

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
