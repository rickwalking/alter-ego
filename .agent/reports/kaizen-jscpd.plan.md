# Kaizen Report — jscpd (frontend duplication gate)
Mode: incident (directed) | Generated: 2026-06-16 | Scope: frontend/src

Task: verify the possibility of adopting jscpd to reduce frontend code
duplication. Ref: https://jscpd.dev/getting-started/agent-skill

## Verdict: FEASIBLE and warranted — adopt as a source-scoped, ratchet-down gate.

## Phase 0 — Signal (measured, not assumed)

Ran `npx jscpd` on `frontend/src` (524 `.ts/.tsx` files):

| Scope | Duplication | Clones | Dup lines |
|-------|-------------|--------|-----------|
| All files (incl. tests) | **7.22%** | 260 | 3223 |
| **Source only** (excl. `*.test.*`, `*.spec.*`, `*.stories.*`) | **1.94%** | 39 | 542 |

**Key finding:** ~73% of the duplication is in **test files** (arrange/setup
boilerplate — `use-editorial-workflow.test.ts` alone = 1257 dup lines). Test
duplication is largely acceptable; **a blocking gate must be source-scoped** or
it will be noisy and pressure devs to DRY up tests in harmful ways. The real,
actionable signal is the **1.94% source** level — small and tractable.

Top SOURCE hotspots (first refactor targets):
- `src/app/(public)/(marketing)/page.tsx` (137)
- `src/lib/api-client.ts` (72)
- `src/modules/.../use-sse-chat.ts` ~ `use-publish-chat.ts` (SSE handling, 47 each)
- `src/app/api/carousels/[id]/workflow/resume/route.ts` ~ `.../start/route.ts` (43 each)

## Failure Classes

| # | Class | Level | Severity | Gate today | Status |
|---|-------|-------|----------|------------|--------|
| 1 | Frontend **source** code duplication | 1.94% / 39 clones | Medium | none | no copy-paste detector in the lint chain or CI |

## Proposals (for approval)

### P1 — Add jscpd as a source-scoped frontend duplication gate  [ratchet: UP] — T2
- **Enforcement:** add `jscpd` devDep + `.jscpd.json`:
  ```json
  { "format": ["typescript","tsx"],
    "ignore": ["**/node_modules/**","**/dist/**","**/*.test.*","**/*.spec.*","**/*.stories.*"],
    "minTokens": 50, "minLines": 5,
    "threshold": 2, "reporters": ["console","json"], "absolute": false }
  ```
  (`threshold: 2` ≈ the current 1.94% source level; the gate fails if duplication
  exceeds it.) The threshold may only **ratchet DOWN** over time — never up.
- **Wiring (single source of truth):** `npm run lint:dup` → chain into `lint`
  (next to `lint:boundaries`); add a `frontend:duplication` gate to
  `scripts/ci/gates.sh`; add a `frontend / Duplication` job to
  `frontend-quality-gates.yml`. Document in `frontend/AGENTS.md` +
  `docs/guides/qa-checkpoints.md`.
- **Ratchet protection:** add jscpd `threshold` to `check-integrity.sh` watched
  keys (higher = loosening) so raising it is flagged like any other gate-loosening.
- **AC:** gate FAILS on a seeded duplicate block; passes at current source level;
  threshold can only decrease.
- **Eliminates:** class #1 going forward (new source duplication blocked).

### P2 — Refactor the top source hotspots  [ratchet: UP] — T2
- Extract shared SSE handling (`use-sse-chat.ts` ~ `use-publish-chat.ts`) and the
  carousel workflow API routes (`resume/route.ts` ~ `start/route.ts`) into shared
  helpers; pay down `api-client.ts` and the marketing page. Then lower the jscpd
  `threshold` toward ~1% (ratchet down).
- **Eliminates:** the existing 1.94% debt; enables a tighter threshold.

### P3 — Advisory (non-blocking) jscpd run on tests  [ratchet: HOLD] — T1 (optional)
- Surface egregious test duplication (the 7.22% figure) as a **non-blocking** PR
  report (like `frontend / Mutation (advisory)`), without forcing test DRYing.

## Rejected (would loosen / miscalibrate)
- ❌ A blocking gate that INCLUDES test files at 7.22% — calibrates the bar on
  boilerplate, creates noise, and pressures harmful test-DRYing. Tests are
  advisory-only (P3), not blocking.
- ❌ Setting `threshold` above the measured source level "to be safe" — that bakes
  in slack; the gate starts at the real number and only tightens.

## Proposed tickets (created only on approval)
- AE-#### — P1 jscpd source-scoped duplication gate (T2, Quality, Frontend/CI)
- AE-#### — P2 refactor top duplication hotspots + lower threshold (T2, Refactor, Frontend)
- AE-#### — P3 advisory jscpd test-duplication report (T1, Task, Frontend/CI) [optional]
