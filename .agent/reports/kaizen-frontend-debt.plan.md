# Kaizen Report — frontend-debt

> **RENUMBER NOTE (2026-06-17):** tickets below were renumbered to free IDs to
> avoid collision with PR #29 (which owns AE-0172..0182).
> Map: P1→**AE-0183**, P2→**AE-0184**, P3a→**AE-0185**, P3b→**AE-0186**,
> P4→**AE-0187**, P5→**AE-0188**. References to AE-0172..0177 below are historical.
Mode: incident (directed) | Generated: 2026-06-17 | Scope: frontend/

User-reported classes + a full eslint/depcheck sweep. The "proper way to get
this information" is to **measure each class with the right detector**, not work
from an anecdotal list:

| Class | Detector (the proper tool) | Command |
|-------|----------------------------|---------|
| Unused deps | depcheck / knip | `npx depcheck --json` |
| fetch vs TanStack Query | grep hooks + query adoption | `grep -rlE 'fetch\(' src/**/hooks` |
| Oversized functions / lint debt | eslint JSON, aggregated by rule | `npx eslint src -f json` → group by `ruleId` |
| isLoading vs Suspense | grep + ADR check | `grep -rlE 'isLoading' src` vs `<Suspense>` |

## Failure Classes (measured, ranked)

| # | Class | Signal | Sev | Gate today |
|---|-------|--------|-----|-----------|
| C1 | Unused deps (v1/shadcn leftovers) | depcheck: 12 unused (8 `@radix-ui/*`, `framer-motion`, `react-hook-form`, `client-only`, `server-only`); **0 radix imports remain in src** | Med | none |
| C2 | Raw `fetch` in hooks vs TanStack Query | 2 hooks (`identity/use-auth.ts`, `blog/use-blog-post-editor.ts`); 21 already on Query | Med | none |
| C3 | `max-lines-per-function` mis-calibrated for JSX + giant components | 120 findings; `HomePageContent` **1133**, `CalendarPage` **338**, `BlogPostsPage` 229 (limit 40 on page.tsx) | High | NONE — `lint:changed` uses `--quiet` (warnings suppressed); see skeptical review |
| C4 | `isLoading` instead of Suspense (ADR-010 drift) | **39** files manual loading vs **1** `<Suspense>`; ADR-010 accepted | Med | none |
| C5 | Latent lint debt (sweep bonus) | no-unnecessary-condition 70, prefer-nullish 55, **no-floating-promises 17** (possible bugs), no-misused-promises 15, complexity 38 | Med | NONE — `lint:changed` uses `--quiet` (warnings suppressed); see skeptical review |

## Proposals (for approval)

### P1 — Remove unused deps + add a dead-dependency gate  [ratchet: UP] — T2
- Remove the **confirmed-unused runtime deps**: 8 `@radix-ui/*` (0 imports),
  and verify+remove `framer-motion`, `react-hook-form`, `client-only`,
  `server-only`.
- ⚠️ **devDeps need manual triage** — depcheck's 10 devDep "unused" are mostly
  config-used false positives (`tailwindcss`, `@tailwindcss/postcss`,
  `typescript-eslint`, `eslint-plugin-react-hooks`, `@commitlint/*`,
  `@stryker-mutator/vitest-runner`, `prettier-plugin-tailwindcss`). Keep those;
  only `@hookform/resolvers` likely goes (pairs with react-hook-form).
- Add a `frontend:deadcode-deps` gate (depcheck or **knip**) to `gates.sh` + CI,
  with an allowlist for config-only devDeps so it doesn't false-positive.
- **AC:** gate FAILS on a seeded unused dep; passes after removals.

### P2 — Migrate the 2 fetch hooks + forbid fetch in hooks  [ratchet: UP] — T2
- Migrate `use-blog-post-editor.ts` (and `use-auth.ts` unless an auth-flow
  exception is justified) to TanStack Query.
- Add eslint `no-restricted-syntax`/`no-restricted-globals` forbidding `fetch(`
  under `src/**/hooks/**`.
- **AC:** rule FAILS on a seeded `fetch(` in a hook; both hooks on Query.

### P3 — Calibrate max-lines-per-function for JSX + refactor the giants  [ratchet: UP] — T2 (+ refactors)
**This addresses "should not affect tsx" WITHOUT loosening.** Two parts:
- **P3a (calibrate):** raise the component threshold to a *defensible* number
  (proposed ~150 for `src/app/**/page.tsx` + component `.tsx`, with
  `skipBlankLines+skipComments`; keep 40/30 for pure logic in `lib`/`hooks`).
  A 40-line cap on JSX bodies is a false-positive generator; ~150 keeps a real
  ceiling. Add the threshold to `check-integrity.sh` so it can only ratchet DOWN.
- **P3b (refactor the real offenders):** split `HomePageContent` (1133),
  `CalendarPage` (338), `BlogPostsPage` (229) into subcomponents/hooks to land
  under the calibrated threshold. (Separate refactor tickets / a small epic.)
- **AC:** after P3a no false positives on reasonable components; after P3b the
  three giants pass; threshold can only decrease.

### P4 — Suspense migration ratchet (ADR-010 enforcement)  [ratchet: UP] — T3
- Block **NEW** manual-loading patterns in changed files (eslint restricted
  pattern or a check-integrity-style scanner), grandfathering the 39 existing.
- Incremental migration epic toward `<Suspense>` per ADR-010 + the
  loading-patterns guide (AE-0146).
- **AC:** a seeded new `isLoading` data-fetch in a changed file is flagged;
  existing 39 not blocked; migration tracked.

### P5 — Burn down latent lint debt (correctness first)  [ratchet: HOLD] — T2
- Paydown epic for the warn-level findings that are already ERROR on changed
  files. **Prioritize `no-floating-promises` (17) + `no-misused-promises` (15)**
  — those are likely real async bugs, not style.
- **AC:** counts driven to 0 (or justified per-line), no rule disabled.

## Rejected (would loosen the bar — INVARIANT)
- ❌ Set `max-lines-per-function` to **off** for `.tsx`, or bump it to 1133 to
  silence `HomePageContent`. That's gaming. The fix is calibrate-to-defensible +
  refactor (P3), not exempt.
- ❌ Disable `no-unnecessary-condition` / `prefer-nullish-coalescing` to clear C5.
- ❌ Remove a devDep depcheck flagged without verifying it isn't config-used
  (would break Tailwind/eslint/commitlint/stryker).

## Proposed tickets (created only on approval)
- AE-#### — P1 remove unused deps + dead-dependency gate (T2, Frontend/CI)
- AE-#### — P2 migrate fetch hooks + forbid fetch in hooks (T2, Frontend)
- AE-#### — P3a calibrate max-lines-per-function for JSX + ratchet (T2, Frontend/CI)
- AE-#### — P3b refactor giant components (HomePageContent/CalendarPage/BlogPostsPage) (T2 epic, Frontend)
- AE-#### — P4 Suspense migration ratchet + epic (T3, Frontend)
- AE-#### — P5 burn down latent lint debt, async-correctness first (T2, Frontend)
