# Cold Critic Review

> **RENUMBER NOTE (2026-06-17):** tickets below were renumbered to free IDs to
> avoid collision with PR #29 (which owns AE-0172..0182).
> Map: P1→**AE-0183**, P2→**AE-0184**, P3a→**AE-0185**, P3b→**AE-0186**,
> P4→**AE-0187**, P5→**AE-0188**. References to AE-0172..0177 below are historical.

## Verdict
**WARN** — the plan is well-structured and clearly written by someone who understands the codebase, but it contains material factual errors about current CI enforcement, proposes enforcement mechanisms that don't exist yet (requiring new infrastructure), and makes at least one claim that soft-loosens the quality bar if implemented naively. I do not BLOCK because the core direction is correct. But several tickets need their ACs tightened before approval.

---

## Findings

### [BLOCKER] AE-0177 (P5): "already ERROR on changed files" is factually wrong — `lint:changed` uses `--quiet`

- **Assumption:** The plan claims these warn-level findings *"are already ERROR on changed files"* and that P5 is a `[ratchet: HOLD]`. The `gate_frontend_lint_changed` function in `gates.sh` runs `npm run lint:changed`, which executes `node ../scripts/ci/eslint-changed.mjs`. That script runs `npx eslint --quiet ...files` (line 33 of `eslint-changed.mjs`).
- **Risk:** `--quiet` **suppresses all warnings**. It only reports errors. So `no-floating-promises` (warn), `no-misused-promises` (warn), `no-unnecessary-condition` (warn), etc. are **silently ignored** on changed files today. The plan's "Gate today: warn → ERROR on changed files" column for C5 is **false**. P5 is not a `HOLD` (maintaining an existing gate) — it's a `UP` (new enforcement) because these findings have **zero enforcement today**. This mis-framing could lead a reviewer to dismiss P5's priority.
- **Impact:** If approved under the `[ratchet: HOLD]` label, the ticket would get lower priority than it deserves. These are actual bugs (17 floating promises) with no existing CI gate.
- **Suggested mitigation:** Reclassify P5 as `[ratchet: UP]` (new enforcement, not holding existing). Change `--quiet` to `--max-warnings=0` in `lint:changed` **after** the burn-down is complete, or run a separate gate that promotes these specific rules to `error` on changed files.
- **Open question for author:** Was the `--quiet` suppression known? If so, the plan should explicitly discuss whether `lint:changed` should switch to `--max-warnings=0` post-cleanup, or whether a separate `lint:changed:strict` gate is needed. If it was not known, the whole "Gate today" column for C5 is unreliable.

---

### [BLOCKER] AE-0176 (P4): Enforcement mechanism is underspecified and may be unimplementable with current tooling

- **Assumption:** The plan says *"Block NEW manual-loading patterns in changed files (eslint restricted pattern or a check-integrity-style scanner), grandfathering the 39 existing."*
- **Risk:** "isLoading" is not a single syntactic pattern — it's a property name used in type definitions, component props, hook return values, and test fixtures. My grep found 60 matches, several of which are in test files (`*.test.tsx`) and type definitions (`types.ts`). Writing an ESLint rule that catches *data-fetching* loading states but not legitimate local-form-submission loading states or type annotations is **hard**. The plan offers no concrete selector, no AST pattern, and no fallback. `check-integrity.sh` is a unified-diff scanner that catches suppression/disable tokens — it cannot detect `isLoading` as a semantic pattern without a lot of custom machinery.
- **Impact:** Without a specific mechanism, this ticket's AC ("a seeded NEW isLoading data-fetch in a changed file is flagged") cannot be verified. The epic will stall on implementation, or a too-broad rule will generate false positives on perfectly legitimate local loading states (e.g., submit-button disabled-while-saving patterns like `ChangePasswordDialog`).
- **Suggested mitigation:** Define the exact AST pattern/selector before accepting the epic. For example, target `VariableDeclarator[id.name="isLoading"]` with an ancestor of `useState("useState")` call within `useEffect` or `fetch` — this would catch the anti-pattern without flagging local form submission states. Alternatively, the "isLoading prop from useQuery" pattern (which is the legitimate TanStack Query pattern) uses an `isLoading` property from a hook return — that should be allowed.
- **Open question for author:** How do you distinguish `isLoading` as a *data-fetching state* (which should be Suspense) from `isLoading` as a *local mutation/submission state* (which is legitimate)? The plan grandfathers 39 but the grep shows 60 hits — which 21 are excluded and why?

---

### [WARN] AE-0174 (P3a): The `check-integrity.sh` ratchet for `max-lines-per-function` does not exist yet

- **Assumption:** *"Add the threshold to `check-integrity.sh` so it can only ratchet DOWN."*
- **Risk:** The current `check-integrity.sh` has direction-aware threshold detection (lines 138-143) for patterns like `fail-under`, `max-complexity`, `max-args`, `BASELINE_*`. But `max-lines-per-function` is **not** in `HIGHER_IS_GAMING` or `LOWER_IS_GAMING`. A developer could bump the threshold to 200, commit it, and the integrity scanner would not flag it. The mechanism needs to be *built*, not just *invoked*. This is a dependency between AE-0174 and a modification to `check-integrity.sh` that is not tracked as a subtask.
- **Impact:** The AC "Threshold registered in check-integrity.sh (raise = flagged)" cannot be validated unless the detector is extended. If the threshold is added to eslint config but the integrity scanner is not updated, the ratchet is aspirational.
- **Suggested mitigation:** Either (a) make AE-0174 explicitly depend on a subtask that adds `max-lines-per-function` to `HIGHER_IS_GAMING` in `check-integrity.sh`, or (b) note that the integrity scanner will need an update and document the exact regex that will be added. Without this, the commit that raises the limit is not review-blocked.
- **Open question for author:** Are we adding `max-lines-per-function` as a new key to `HIGHER_IS_GAMING`? If so, we need to ensure the regex `r"max-lines-per-function"` is added. But `HIGHER_IS_GAMING` currently only matches keys like `max-complexity`, `max-args` — the `eslint.config.mjs` does not use inline numeric values for `max-lines-per-function` in a way the current diff scanner can pair (the value is in a config object: `{ max: 40, ... }`). The paired diff scanner looks for `removed numeric → added numeric` on the same config file line. A change from `max: 40` to `max: 150` would be detected as two lines by the diff parser (line with `max: 40` removed, line with `max: 150` added in the same file). This should work for `eslint.config.mjs` — but **confirmation that the parser handles JSON-like config values is needed.**

---

### [WARN] AE-0172 (P1): `framer-motion` and `react-hook-form` are in the declared tech stack — removal needs stronger evidence than depcheck alone

- **Assumption:** `depcheck` reports 0 imports for `framer-motion`, `react-hook-form`, `client-only`, `server-only`, therefore they are "confirmed-unused runtime deps."
- **Risk:** `frontend/CLAUDE.md` explicitly lists `framer-motion` under "Animation | Framer Motion" (line 56) and `react-hook-form` under "Forms | React Hook Form + Zod" (line 51) as core tech stack. These may be used indirectly — framer-motion could be referenced via `motion.div` in JSX (which depcheck *can* detect if it parses TSX), or react-hook-form's `useForm` may be imported in page components depcheck missed (e.g., if they are in files that use dynamic imports or are type-only). `client-only` and `server-only` are Next.js ecosystem packages that throw at build time if imported on the wrong side — they are used by adding `import "server-only"` at the top of files to enforce boundaries. If these are genuinely unused, removing them is correct. But if depcheck missed a usage (e.g., `"use client"` boundary enforcement), removing them could cause silent build failures or incorrect tree-shaking.
- **Impact:** If any of these are actually used but depcheck missed them, `npm run build` would fail or, worse, pass silently but break boundary enforcement at runtime.
- **Suggested mitigation:** The ticket says "verify+remove" — but the AC does not include an explicit **verification step** like `npm run build && npm run typecheck && npm run test` after each removal. Add: "Each dep removed one at a time, with `npm run build` + `npm run test` green after each removal, to isolate which removal breaks the build." Also run a wider scan — `rg "framer-motion" --type tsx` in addition to depcheck.
- **Open question for author:** Were `client-only` / `server-only` imports checked via `rg "from \"client-only\""` or only via depcheck? These packages are typically consumed as `import "server-only"` (no `from`) and depcheck may parse them differently.

---

### [WARN] AE-0173 (P2): `use-blog-post-editor.ts` does NOT use raw `fetch` — the plan's framing is inaccurate

- **Assumption:** The plan says "2 hooks still use raw fetch."
- **Risk:** Reading the actual source: `use-blog-post-editor.ts` calls `useBlogPosts()` (line 22), which presumably uses TanStack Query. It then synchronizes API data into local editor state via `useEffect` (lines 36-46). This is a **state-initialization** pattern, not a raw-fetch pattern. The `handleSave` function calls `update()` and `refetch()` from `useBlogPosts` — not raw `fetch`. The actual raw-fetch violation is in `use-auth.ts` (lines 13, 36). The plan's claim is **2 hooks on fetch, 21 already on Query** but the second hook is not fetch — it's downstream of Query and just seeds local state. Migrating `use-blog-post-editor.ts` to "TanStack Query" doesn't solve anything because it already *uses* Query through `useBlogPosts`. The problem here is `useEffect` for state synchronization, which is a different concern than raw fetch.
- **Impact:** If a developer tries to "migrate `use-blog-post-editor.ts` to TanStack Query" as the ticket says, they'll find it already is — and will waste time refactoring the local-editor-state-sync pattern away, potentially breaking the editor's undo/isolated-draft behavior (the whole point of local state is that save and display state differ during editing).
- **Suggested mitigation:** Split AE-0173 into two: (a) migrate `use-auth.ts` to TanStack Query (or document the auth exception), and (b) separately address `use-blog-post-editor.ts`'s useEffect state-sync pattern (which belongs under P4/Suspense migration, not P2). The `no-restricted-syntax` rule forbidding `fetch(` in hooks is fine for `use-auth.ts` but won't catch `use-blog-post-editor.ts` because it doesn't use `fetch` — it uses `useEffect` + `useBlogPosts`. 
- **Open question for author:** Does the `no-restricted-syntax` rule need to also block `useEffect` calling `refetch()` to cover the editor hook, or is that a separate enforcement under P4?

---

### [INFO] AE-0175 (P3b): Zero behavioral change AC conflicts with the refactor motivation

- **Assumption:** "No behavior/visual changes (pure refactor — snapshots/tests must be unchanged)."
- **Risk:** The very motivation for P3b is that these components are too large to be maintainable. Splitting a 1133-line component into subcomponents *will* change its test surface — what were internal state variables become props, what were inline conditionals become subcomponent logic. "Zero behavioral change" is a reasonable *goal* but an unrealistic *AC* for a refactor of this magnitude. If tests are snapshot-based, even whitespace changes in the split will break them. If they are behavior-based, subcomponents that were previously untestable (internal to the giant) will now be testable — but "untouched" tests may not cover the new boundaries.
- **Impact:** The "tests green" AC could be gamed trivially by not splitting into independently-testable units, or by not adding new tests for extracted logic. The epic could produce new large-but-slightly-less-large files that still violate the principle.
- **Suggested mitigation:** Change the AC to "Behavior is preserved (existing tests pass without modification); extracted units have >= 90% branch coverage; component count in tests may increase." This ensures actual refactoring.
- **Open question for author:** What is the expected component-count after the split? If `HomePageContent` (1133 lines) becomes a barrel with 6 subcomponents, that meets the letter of the AC but may not improve maintainability proportionally.

---

## Missing evidence

1. **Raw depcheck JSON output.** The plan references "depcheck: 12 unused" but the actual JSON output is not in the report or attachments. Without seeing which exact 12 deps depcheck flags (including which of the 8 radix packages), the verification step in AE-0172 cannot be independently confirmed. The plan also says "0 radix imports remain in src" — this should be the `rg` command used, to make it independently reproducible.

2. **Baseline list of the 39 isLoading files.** P4 grandfathers "39 existing" files. My grep found 60 matches. The delta needs to be explained: which 21 are test files, type definitions, or legitimate local-state loading flags that should not be migrated? Without the authoritative list, a developer cannot tell whether they're adding a new violation or touching a grandfathered one.

3. **Actual fetch usage in use-blog-post-editor.ts.** The plan claims 2 hooks use raw `fetch`, but source inspection shows only 1 (`use-auth.ts`). The plan should acknowledge this discrepancy.

4. **How `lint:changed` currently handles warnings.** The plan claims warn-level findings are "ERROR on changed files" but `lint:changed` uses `--quiet`. This factual error pervades the priority framing.

---

## Residual risks if plan proceeds unchanged

1. **P5 burn-down fails to fix actual bugs.** Because P5 is framed as a `HOLD` (maintaining an existing gate), it gets lower priority. The 17 floating promises and 15 misused promises are likely real bugs. If the epic is deprioritized behind P3/P4 refactors, actual correctness issues remain unaddressed for months.

2. **Incremental Suspense migration (P4) stalls on grandfathering.** The 39-file grandfather list is not captured in the plan. If a developer touches one of those files for another reason (e.g., the P3b CalendarPage refactor), they face a choice: migrate to Suspense (scope creep) or be blocked by their own refactor. The plan has no coordination between P3b and P4.

3. **`@hookform/resolvers` left behind.** If `react-hook-form` is removed (P1) but `@hookform/resolvers` is missed or kept because "it's a devDep, let's not touch it," the dead-devDep gate would need to be updated to catch it later. The plan should make explicit that P1 removes both or neither.

4. **P3a threshold of 150 may still generate false positives.** A 150-line component is large by any standard (CLAUDE.md says "max 20 lines per function"). While better than 40, the transition from "120 findings" to "0 findings" should be verified with a count of how many components fall between 40 and 150 lines. If the threshold is too high, the ratchet effect is meaningless because nobody will ever approach it.

5. **No coordination with the backend CI changes** — `check-integrity.sh` currently has a single `HIGHER_IS_GAMING` list. Adding `max-lines-per-function` there would also affect any backend config that uses those words (unlikely but possible). The change should add a frontend-scoped pattern or a new category.

---

*Review completed 2026-06-17. I held the plan to the kaizen invariant (quality rules only ratchet UP or HOLD, never DOWN) and identified no violations — but several mechanisms are incomplete or mis-framed.*
