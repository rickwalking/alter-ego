# Architecture Plan — Suspense + fetch migrations & docs reorganization
Mode: research+plan | Read-only | 2026-06-18 | For human approval (no tickets created yet)
Grounding scans: 3 parallel Explore agents (counts/paths below are from live code).

## TL;DR + scope corrections (architect honesty)

1. **The Suspense problem is real but SMALLER than the symptom suggests.** Only
   **~2–3 genuine initial-data-load violations** of ADR-010 exist. Most `isLoading`
   sightings are **mutation pending flags** (button-disabled-while-saving), which
   ADR-010 **explicitly allows**. A codebase-wide "remove isLoading" would be wrong
   — it would break legitimate mutation UX. Migrate the true initial-load cases only.
2. **fetch and Suspense CONVERGE on one cluster.** The admin user-management area
   (`app/(admin)/admin/users/page.tsx` + 4 `components/admin/*-dialog.tsx`) is at
   once the largest raw-`fetch(` cluster (5 of 7 violations) AND the one *large*
   Suspense violation. **One `src/modules/admin/` TanStack Query layer fixes both.**
3. **Docs reorg is a genuine T3 epic** (~12–15h): ~11 delete/archive candidates,
   6 oversized guides, missing folder indexes, ADR-011/012 unindexed, a few stale docs.
4. These extend existing tickets — **AE-0184** (fetch, Review, narrow) and **AE-0187**
   (Suspense ratchet, T3) — rather than inventing parallel ones. Docs is net-new.

## Current state (from scans)
- Suspense adoption: 3/255 `.tsx` use `<Suspense>`; 1 uses `useSuspenseQuery`. Reference impl: `modules/knowledge` (`useDocuments()` + `useSuspenseQuery` + `<Suspense>`).
- `fetch(`: 14 call sites — 7 MIGRATE (client), 7 LEGIT-INFRA (api-client, server-fetch, sse-client, route handlers). ESLint rule (AE-0184) already blocks `fetch(` under `src/**/hooks/**`.
- Infra ready: `QueryProvider` configured (`components/providers/query-provider.tsx`); module hook pattern established (`modules/identity/{queries.ts,hooks/}`).
- Docs: 12 ADRs (0009 still "Proposed"; 011/012 missing from CLAUDE.md index); 6 guides 1.7k–2.3k lines; plans/ mixes active + historical; 3 stray root-level `.md`.

---

## Proposed work — three threads

### THREAD A — Data-layer compliance (fetch → TanStack + Suspense)
Closes the genuine AE-0184 (fetch) + AE-0187 (Suspense) violations. Sequence A1→A2; A3 optional.

**A1 — `src/modules/admin/` TanStack Query layer + migrate admin user mgmt  [T2]**
- Create `modules/admin/queries.ts` (`adminKeys`, query/mutation options) + `hooks/use-admin-users.ts` (1 `useQuery`/`useSuspenseQuery` for the list + 4 mutations: create/edit/delete/reset-password) following the `modules/identity` pattern + the central `api-client`.
- Migrate `app/(admin)/admin/users/page.tsx`: remove `useState(isLoading)`+`useEffect(fetch)`; use `useSuspenseQuery` + wrap the table in `<Suspense>` (+ error boundary). **Fixes the raw-fetch-in-useEffect AND the ADR-010 initial-load violation in one move.**
- Migrate the 4 `components/admin/*-dialog.tsx` to `useMutation` (removes 4 raw `fetch(`); keep their pending flags as `mutation.isPending` (legit).
- **ACs:** 0 raw `fetch(` in admin components; `users/page` initial load via Suspense (no manual `isLoading` branch); all admin CRUD behavior preserved; ESLint fetch rule green; gates.sh frontend green. **AE-0180 N/A** (no new rule), but add/extend hook unit tests (MSW) for the new query/mutations.
- Effort: ~1 day. Closes 5/7 fetch MIGRATE + 1/2 Suspense violations.

**A2 — Migrate the remaining initial-load components to Suspense  [T2]**
- `modules/publishing/blog/components/version-history-sidebar.tsx` — replace `useEffect`+`useState(loading)` with `useSuspenseQuery` + parent `<Suspense>`.
- `modules/publishing/distribution/components/regenerate-strategy-section.tsx` — the **MIXED** case: has a `<Suspense>` boundary but uses `useQuery` (so it never suspends) + a manual `if (isLoading)` branch. Switch `useAvailableStrategies()` → `useSuspenseQuery` variant and drop the manual branch. Keep the regenerate **mutation** as-is.
- **ACs:** both load initial data via Suspense; no manual initial-load `isLoading` branches remain; mutation flags untouched; gates green.
- Effort: ~1–2 days. Closes the 2nd Suspense violation + the mixed case.

**A3 — Login + carousel-image-download (optional / low priority)  [T1]**
- `app/login/page.tsx`: optionally move the `/api/auth/token` POST into a `postLogin` mutation hook (mirrors existing `postLogout`). NOT ESLint-blocked (not in a hook); cosmetic consistency.
- `horizontal-carousel-viewer.tsx` raw `fetch(` for image download: **document as a sanctioned exception** (one-shot asset download, not shared state) rather than force into Query. Decision to record, not necessarily code.
- Effort: ~0.5 day or defer.

**Enforcement (anti-regression) — note, not a blocker:** ADR-010 itself says a hard
Suspense lint is brittle/out-of-scope. The realistic ratchet is (a) the QA checkpoint
added in AE-0225, plus (b) extending the existing `no-restricted-syntax` to flag
`useEffect` containing `fetch(`/`await …(` for **initial** loads under `components/`
+ `app/` (not just `hooks/`). Propose as a *follow-up* only after A1/A2 drive the
count to 0 (so the rule lands green) — same "fix first, then ratchet" discipline as the wave. Would need an AE-0180 rule-fires test.

### THREAD B — Documentation reorganization & cleanup  [T3 EPIC → planner-skill]
Recommend routing through `/planner-skill` for the epic breakdown; suggested tickets:

**B1 — Quick wins  [T1]:** add ADR-011 & ADR-012 to the CLAUDE.md ADR index; add `Status:` headers to unmarked plans (e.g. `backend/carousel-pipeline-plan.md`); decide ADR-0009 `Proposed`→`Accepted`. Low risk, high value.

**B2 — Delete/archive superseded docs  [T2]:** create `docs/archive/`; move/delete the ~11 superseded items (PROFESSIONAL_PIVOT_PLAN, plan-sse-migration-v2, cloudflare-ws-debug, BACKEND_IMPLEMENTATION_PLAN, AGENTIC_REFACTOR_PLAN, the superseded carousel/ae-0040 stubs, rollback/ + assessment/). **Guardrail:** before each delete, grep for inbound links (README, CLAUDE.md, other docs) and fix/redirect them — the scan found several are linked. Prefer `git mv` to `archive/` over hard delete for the large historical records; hard-delete only stubs with no inbound links.

**B3 — Folder indexes + plans active/historical split  [T2]:** add `INDEX.md` to each major folder; reorganize `plans/` into `active/` + `historical/` (Phases 1–6 are Done). Update README + CLAUDE.md `docs/plans/...` links that move.

**B4 — De-bloat the 6 oversized guides  [T2, can be its own mini-epic]:** VITEST (2333), ZOD (2009), react-2026 (1939), react-components (1765), style-guide (2134), minimizing-useeffect (2107) all violate the <400-line norm. Split each into a <300-line quick-ref + a linked deep-dive, or trim. Largest chunk; do last / incrementally.

**B5 — Fix stale content  [T1]:** `API_CONTRACT.md` still references removed ChatInterface/TopicForm; verify `frontend-legacy-removal.md` status against the live tree and mark Done if the legacy components are gone; resolve any TODO/MISSING markers in `qa-checkpoints.md`.

---

## Sequencing recommendation
1. **A1** first (highest leverage — clears 5 fetch + 1 Suspense violation, builds the admin module others can follow).
2. **A2** next (finishes the Suspense initial-load violations → count 0).
3. **B1 + B5** quick-win docs (cheap, independent, parallelizable with A).
4. **B2 → B3** docs structure (B2 before B3 so indexes reflect the final layout).
5. **B4** guide de-bloat (largest, lowest-risk, incremental).
6. **A3** + the optional Suspense `useEffect`-fetch lint ratchet **last** (after A1/A2 make it land green).

## Dependencies
- A2's regenerate-strategy fix is independent of A1; version-history independent too — A2 can parallelize with A1 once the `useSuspenseQuery` pattern is settled.
- B3 depends on B2 (don't index files about to move/delete).
- The Suspense ratchet lint depends on A1+A2 (must be 0 violations first).

## ADR check
- No NEW ADR needed: A-thread executes the **already-accepted ADR-010** (Suspense) and the fetch standard behind AE-0184. B-thread is docs hygiene.
- B1 should flip **ADR-0009** `Proposed → Accepted` (decision, with rationale) since the modular-monolith is live.

## Risks / notes
- **Don't over-migrate Suspense.** Verify each candidate is an *initial data load* before converting; leave mutation pending flags alone (the scan already separated them).
- **Doc deletion is irreversible-ish** — use `archive/` + inbound-link checks; hard-delete only no-inbound-link stubs.
- A1 touches the admin panel (security-adjacent) — keep server-side authz unchanged; this is a client data-layer refactor only. QA security dimension applies.

## Tier verdict
- Thread A: **two T2 tickets (A1, A2)** + one optional T1 (A3). Fits under existing AE-0184/AE-0187 scope — recommend updating those rather than net-new epics.
- Thread B: **T3 epic** → hand to `/planner-skill` to emit B1–B5 (mix of T1/T2).
