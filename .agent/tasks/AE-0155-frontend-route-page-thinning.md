# AE-0155 — Frontend: route-page thinning (app pages -> thin composition)

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

Reduce app/**/page.tsx to thin composition components over module hooks/contracts, where it can be done without behavior risk (Phase 7 kept pages as-is).

## Problem

Phase 7 kept route pages unchanged to stay behavior-preserving; some pages still contain data/composition logic that belongs in module hooks, violating the 'route pages are thin composition' exit-gate intent.

## Scope

For pages with extractable data/composition logic, move it into the owning module (hooks/contracts) and leave the page as thin composition; keep App Router URLs + segment config + rendered output byte-identical. Skip pages where thinning risks behavior.

## Non-Goals

- No App Router URL or segment-config change; no observable behavior change.
- No exhaustive rewrite — only safe extractions.

## Modularization Alignment (2026-06-16)

Phase 8 of the modularization plan (§Phase 8 "Remove legacy layers and adapters") — the final phase, after
Phases 0-7 merged (PRs #15-#21). Removes the temporary migration scaffolding to zero. Class A (safe cleanup) is
behavior-preserving and holds the existing green gates with down-only ratchets; Class B (auto-publish cutover +
destructive column drop) is consent-gated + drain-gated (ADR-0008). See `docs/plans/phase-8-legacy-removal.md`.

## Acceptance Criteria

- [x] Targeted route pages SHALL become thin composition over module hooks (no inline data logic)
- [x] App Router URLs + segment config unchanged (url:check 26); rendered output byte-identical
- [x] typecheck + lint + 822 tests + build green; boundary 0

## Gherkin Scenarios

Not applicable — legacy-removal cleanup; verified by the green-gate safety net (back-end gates.sh + check-integrity + arch-ratchet; front-end typecheck/lint/boundaries/url/circular/tests/build).

## Dependencies

- Blocks: —
- Blocked by: AE-0153
- Related: AE-0152

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-16

Ticket created by planner (Phase 8 breakdown).

## Files Touched

- NEW `frontend/src/modules/publishing/blog/hooks/use-blog-post-editor.ts` — `useBlogPostEditor(postId)`: encapsulates the blog-post editor composition (load via `useBlogPosts`, mirror editable fields into local state, `handleSave`/`handleRestore`). `"use client"`.
- `frontend/src/modules/publishing/blog/hooks/types.ts` — added `UseBlogPostEditorResult` (return type colocated, keeps component-type-location at 0).
- `frontend/src/modules/publishing/index.ts` — barrel exports `useBlogPostEditor` + `UseBlogPostEditorResult`.
- `frontend/src/app/dashboard/blog-posts/[id]/edit/page.tsx` — thinned: removed the inline `useState`×6 / `useEffect`×2 / `handleSave` / `handleRestore`; the page now destructures the hook and renders. Rendered output + behavior byte-identical.

## Test Evidence

- `npm run typecheck` — clean.
- `npm run lint` — clean: boundary OK (0/0/0 new), URL inventory OK (**26 routes unchanged**), circular OK (0 cycles), component-type-location OK (0/0/0).
- `npm run test` — 75 files, 823 passed.
- `npm run build` — succeeded (added the required `"use client"` to the new hook — it is reachable from a Server Component via the publishing barrel; caught by the production build).
- `npm run check:legacy` — passed; `npm run test:e2e:auth` — 7 passed.
- `check-integrity.sh frontend` — PASS, 0 blockers / 0 warnings.

## QA Report

Pending (Phase 8 end-of-phase QA on the full branch).

## Decision Log

- **Conservative scope (per the ticket):** thinned the clearest, lowest-risk offender — the blog-post edit page — extracting its data/composition logic into a colocated module hook. Output byte-identical.
- **Deliberately SKIPPED (thinning would risk behavior or isn't data-logic):**
  - `app/dashboard/create/[id]/page.tsx` — already delegates to extracted helpers + module hooks; the remaining state is workflow/SSE-intertwined (retry handler, phase resolution) → higher risk, out of "safe extractions only".
  - `app/dashboard/blog-posts/page.tsx` — its logic is light and the extraction would require widening another module's contract (`DashboardBlogPost` is not exported from the `editorial-operations` barrel) + cross-module coupling; the page is otherwise heavy presentational JSX, not data logic.
  - `app/(public)/(marketing)/page.tsx` (1210 lines) — static landing markup, no data logic.
- **`"use client"` on the new hook:** required because the publishing barrel is also imported by Server Components; the hook uses `useState`/`useEffect`. Caught by the production build (not by tsc/vitest), reinforcing that `npm run build` is part of the gate.

## Blockers

None.

## Final Summary

Route-page thinning (conservative): extracted the blog-post edit page's inline editor state/effects/handlers into a new `useBlogPostEditor` module hook (publishing), leaving the route page as thin composition over the contract — behavior + rendered output byte-identical. Other candidate pages were deliberately left (workflow/SSE risk, cross-module-contract cost, or static markup) and documented. App Router URLs unchanged (26); typecheck, lint (boundary 0 / circular 0 / component-types 0), 823 tests, build, check:legacy, and the AE-0165 auth e2e all green.
