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
deferral (see below). The legacy `src/features/*` re-export shims and the
`_example/` boundary anchor were removed in Phase 8 (AE-0153); all consumers now
import `@/modules/<context>` directly. Remaining Phase 8 follow-ups (exhaustive
component re-homing, route-page thinning, and frontend `identity` consolidation)
are tracked under their own tickets.

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
of `npm run lint`) enforces this. It scans the `modules` layer and treats `app/`
as a consumer (the legacy `features` layer was removed in Phase 8 / AE-0153, so
its `existsSync`-guarded scan is now a no-op):

| Layer           | Owner attribution            | Rule                                                                          |
| --------------- | ---------------------------- | ----------------------------------------------------------------------------- |
| `src/modules/X` | `@/modules/X`                | a module must not import another module's **internal** (`@/modules/Y/<deep>`) |
| `src/app`       | consumer (no owning context) | may import a module's **public contract** only — never `@/modules/Y/<deep>`   |

The ratchet is **down-only**: the grandfathered cross-boundary count
(`scripts/feature-boundary-baseline.json`) may stay equal or shrink, never grow.
Module-internal and `app/`→module-internal imports are NOT grandfathered — they
fail immediately (there are none today, and none should ever be added).

Regenerate the baseline (only ever to ratchet DOWN) with
`npm run boundaries:baseline`.

## Barrel-import policy (AE-0241)

knip's file-scope sweep flagged several re-export barrels (`index.ts`) as
"unused files" because consumers bypass them with concrete paths. The barrel
question is **asymmetric** (the two ways to resolve it are not equivalent), so it
is settled here as an explicit, documented convention rather than left implicit.

**Decision — two barrel classes, two rules:**

1. **Top-level module barrel** `src/modules/<context>/index.ts` — the **public
   API contract**. Cross-module and `app/` code MUST import through it
   (`@/modules/<context>`), enforced by `lint:boundaries` (see above). It is a
   real entry point and is never "unused".

2. **All other barrels are optional re-export sugar.** The canonical import
   convention is the **concrete path**, and these barrels are a convenience layer
   that may be bypassed. This covers:
   - **Design-system barrels** `src/components/{atoms,molecules}/index.ts` — ~128
     imports already use concrete paths (`@/components/atoms/neon-button`); the
     barrel stays optional (consistent with the `frontend/CLAUDE.md` import table,
     which marks `@/components/atoms` as _optional_).
   - **Module layer sub-barrels** `src/modules/<context>/<layer>/index.ts`
     (e.g. `.../components/index.ts`, `.../hooks/index.ts`) — intentional internal
     aggregation; the top-level module barrel re-exports from concrete files.
   - **Co-located feature/page barrels** `src/app/**/index.ts`
     (e.g. `app/dashboard/create/workspace/index.ts`).

**We do NOT migrate the ~128 concrete imports to barrel-as-contract.** That is a
large, review-heavy change with no behavioral benefit; it would only be
undertaken if the team later chose "barrel as the sole import surface" — a
separate, explicitly-scoped ticket, not assumed here.

**knip config (the enforcement of this decision):** `frontend/knip.json` lists the
optional barrels as `entry` — `src/components/{atoms,molecules}/index.ts`,
`src/modules/**/index.ts`, and `src/app/**/index.ts` — so knip no longer reports
them as false "unused files". (The export-level dead-code ratchet,
`scripts/check-dead-code.mjs` / AE-0152, still catches genuinely unused _exports_
inside any barrel, so marking a barrel `entry` does not hide dead code within it.)

After this change the knip file sweep reports only the live `app/dashboard/personas/*`
route files, which are a separate legacy-UI-removal deferral (AE-0240 Non-Goal),
not barrels.

## Component-type-location convention (AE-0144)

A second down-only ratchet enforces **where component/hook types live** — the
"13x class" from the PR #21 review, where a reviewer left the same comment
("move this interface to an external file") 13 times because nothing in the lint
gate caught inline type declarations.

### The convention

Inside `src/modules/**`, a **component** (`*.tsx`) or **hook** (`use-*.ts`) file
MUST NOT declare object-shape TypeScript types inline. They belong in a
colocated `types.ts` — the pattern the codebase already follows in
`modules/publishing/blog/types.ts`, `modules/quality/types.ts`,
`modules/persona/types.ts`, and `modules/knowledge/components/types.ts`.

```ts
// ❌ forbidden — inline in the component/hook file
interface DocumentCardProps {
  document: Document;
}

// ✅ allowed — colocated types.ts, imported by the component
// document-card.tsx
import { type DocumentCardProps } from "./types";
```

**In scope (a violation):** a non-trivial object-shape declaration —
`interface Foo { ... }` or `type Foo = { ... }` — declared inline in a governed
component/hook file.

**Out of scope (never flagged):** trivial type aliases that are not object
shapes (`type ViewMode = "list" | "create";`, `type Resp = z.infer<...>;`); the
colocated `types.ts` / `types-*.ts` destination files; non-component/non-hook
module files (`constants.ts`, `queries.ts`, `adapters/*.ts`, `lib/*.ts`); test,
spec, and Storybook files; and the design-system Zod prop schemas in
`src/schemas/neon-*.ts` (a separate, legitimate prop pattern).

### Enforcement

`scripts/check-component-type-location.mjs` (run via
`npm run lint:component-types`, part of `npm run lint`) enforces this against the
committed baseline `scripts/component-type-location-baseline.json`. It is also
registered as the standalone gate `frontend:component-types` in
`scripts/ci/gates.sh`, so CI (via the `frontend:lint` job) and `/qa-agent` both
run it from a single source of truth.

The ratchet is **down-only**: the grandfathered inline-declaration count may stay
equal or shrink, never grow. A NEW inline declaration (a file/kind/name not in
the baseline) fails immediately, and the total count may never rise above the
baseline ceiling. The baseline was ratcheted from 61 down to **57** by moving the
four `knowledge` component prop types into `components/types.ts`.

Regenerate the baseline (only ever to ratchet DOWN) with
`npm run component-types:baseline`.

## Identity context — deferred to Phase 8 (AE-0139)

The glossary lists an `identity` bounded context, but there is **no
`features/auth`** to migrate: frontend auth/session lives in `lib/` (the
authenticated fetch / session helpers) and `app/` (route-level guards and
sign-in pages), both of which are route-adjacent and risky to relocate in a
behavior-preserving pass. AE-0139 therefore makes identity a **docs-only**
note: no `modules/identity/` is created and no code moves. Frontend identity
consolidation into a dedicated module is **deferred to Phase 8**.
