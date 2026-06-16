# Kaizen Report — pr21
Mode: incident | Generated: 2026-06-16 | Signal window: PR #21 (Phase 7 — Frontend Alignment)

Source PR: https://github.com/rickwalking/alter-ego/pull/21
21 inline reviewer comments + 1 failing CI gate (`frontend / Security`).
Every review comment slipped PAST the frontend lint gate — i.e. the gates have
blind spots a human had to cover. Kaizen's job: turn each recurring class into an
automated UP-ratchet so it cannot recur.

## Failure Classes (ranked by frequency × severity)

| # | Class | Freq | Severity | Gate that should catch it | Status today |
|---|-------|------|----------|---------------------------|--------------|
| 1 | TS `interface`/`type` declared inline in component/hook files instead of a colocated `types.ts` | **13** | High | (none) | Convention exists (`blog/types.ts`, `quality/types.ts`, `persona/types.ts`) but **no gate** — relies on review |
| 2 | Magic numbers/strings + repeated literals not centralized (`xhr.status>=200`, `"/api"`, magic strings) | 3–4 | High | eslint `no-magic-numbers` | Plugin loadable but **rule disabled**; `HTTP_STATUS` + constants/api.ts already exist, unused here |
| 3 | Manual `isLoading` state instead of React `<Suspense>` | 2 | Medium | (none) | Suspense used once; manual state is the norm; no documented pattern |
| 4 | Nested `if` instead of early returns (`use-upload.ts:43`) | 1 | Low | eslint `no-else-return` / depth | `max-depth=4` too lax; no early-return rule |
| — | `frontend / Security` npm audit (high) CI failure | 1 | High | frontend:security (working) | **Gate worked** — this is a dependency fix, not a rule gap |

Root cause common to #1–#4: **`frontend/CLAUDE.md` documents these rules but the
lint gate enforces none of them** — exactly the QA↔CI drift pattern, one level up.

## Proposals (for approval)

### P1 — Component-type-location gate (flagship)  [ratchet: UP] — T2
- **Root cause:** house convention (`*/types.ts`) is documented, not enforced; 13
  inline interfaces accumulated.
- **Enforcement:** new `frontend/scripts/check-component-types.mjs` modeled on the
  existing `feature-boundary-scan.mjs` (regex + file-walk + **baseline ratchet**).
  Fails when a `.tsx`/hook file declares an exported/non-trivial `interface`/`type`
  instead of importing it from a colocated `types.ts`. A
  `component-types-baseline.json` grandfathers the ~13 existing violations so the
  gate blocks only NEW ones (same diff-scoped philosophy as the integrity ratchet).
- **Files:** `frontend/scripts/check-component-types.mjs` (new),
  `component-types-baseline.json` (new), `package.json` (`lint` chain + script),
  `scripts/ci/gates.sh` (new `frontend:component-types` gate),
  `frontend/AGENTS.md` (rule), `docs/guides/qa-checkpoints.md` (row).
- **AC includes:** the gate FAILS on a seeded new inline interface; baseline
  count only ever decreases.
- **Eliminates:** class #1 (13 → 0 future).

### P2 — Enable magic-number/literal enforcement + centralize shared literals  [ratchet: UP] — T2
- **Root cause:** `@typescript-eslint/no-magic-numbers` not enabled; `API_BASE="/api"`
  duplicated across `use-blog-posts.ts`, `use-rubrics.ts`, `use-personas.ts`;
  `HTTP_STATUS` constants exist but unused at `use-upload.ts:39`.
- **Enforcement:** enable `@typescript-eslint/no-magic-numbers`
  (`ignore:[0,1,-1]`, `ignoreEnums`, `ignoreReadonlyClassProperties`) — error on
  changed files via `lint:changed`; export `API_BASE` from `constants/api.ts` and
  forbid the bare `"/api"` literal elsewhere; migrate `use-upload.ts` to
  `HTTP_STATUS`.
- **Files:** `frontend/eslint.config.mjs`, `frontend/src/constants/api.ts`, the
  three hooks + `use-upload.ts`, `frontend/AGENTS.md`.
- **Eliminates:** class #2 (and the "repeating variable" comment).

### P3 — React data-loading pattern: Suspense ADR + guide  [ratchet: UP/HOLD] — T2 (doc)
- **Root cause:** no documented standard for load states; reliable linting of
  "use Suspense" is hard, so enforce via ADR + guide + review checklist rather
  than a brittle rule.
- **Enforcement:** `docs/decisions/00NN-frontend-data-loading-suspense.md` + a
  `docs/guides/frontend-loading-patterns.md`; add to QA Subagent-2 checklist.
- **Eliminates:** class #4 (Suspense) as a review-checklist item, not a flaky gate.

### P4 — Early-return lint  [ratchet: UP] — T1 (fold into P2's PR if convenient)
- Enable `no-else-return` + `sonarjs/prefer-immediate-return`; consider tightening
  control-flow rules. Fixes class #3.

## Rejected (would loosen the bar — INVARIANT)
- ❌ "Lower `frontend / Security` from `--audit-level=high` to `critical`, or add a
  blanket audit exception" — this is the obvious way to make the red gate green;
  it **loosens** the bar and is rejected. The security failure routes to a normal
  **dependency-fix bugfix ticket**, not a rule change.

## Proposed tickets (created only on approval)
- AE-#### — P1 component-type-location gate (T2, Quality, frontend)
- AE-#### — P2 magic-number rule + centralize API_BASE/HTTP_STATUS (T2, Quality, frontend)
- AE-#### — P3 Suspense data-loading ADR + guide (T2, Quality, frontend)
- AE-#### — P4 early-return lint (T1, Quality, frontend) [optional, can merge into P2]
- AE-#### — Bugfix: resolve frontend npm audit high-severity vuln (T1, Bug, frontend) [normal lane, not kaizen]
