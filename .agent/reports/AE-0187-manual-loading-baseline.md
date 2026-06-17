# AE-0187 — Manual loading-state baseline (ADR-010 grandfather list)

**Ticket:** AE-0187 — Suspense data-loading migration (ADR-010, T3 epic)
**ADR:** [`docs/decisions/0010-suspense-data-loading.md`](../../docs/decisions/0010-suspense-data-loading.md)
**Guide:** [`docs/guides/suspense-data-loading-guide.md`](../../docs/guides/suspense-data-loading-guide.md)
**Scope of this report:** every file under `frontend/src` that uses a manual
loading flag (`isLoading` / `setLoading` / `isPending` / `loading`), classified
so a future ESLint ratchet can grandfather the legitimate set and only block new
data-fetch loading state.

Generated from:

```bash
rg -n "isLoading|setLoading|isPending|\bloading\b" src \
  -g '*.ts' -g '*.tsx' \
  -g '!*.test.*' -g '!*.spec.*' -g '!*.stories.*' -g '!i18n/locales/*'
```

## Classification scheme

| Class | Meaning | Verdict |
|-------|---------|---------|
| **(a)** | **DATA-FETCH loading** — flag driven by initial/refetchable data load (`useEffect`+`setLoading` around a fetch, or a query's `isLoading` rendering an initial skeleton). | **Migration candidate** → `useSuspenseQuery` + `<Suspense>` + error boundary. |
| **(b)** | **Local mutation/submission loading** — flag for a user-triggered action (create/update/delete/submit/login), incl. `useMutation().isPending`. | **Legitimate — KEEP** (guide §"When manual `isLoading` is acceptable"). |
| **(c)** | **Query-API / prop / type-only** — `isLoading`/`isPending` re-exposed from a `useQuery` wrapper hook, a presentational `loading` prop, or a type/Zod field. | **Not a violation.** |

## Counts per class

| Class | Files | Verdict |
|-------|-------|---------|
| **(a) DATA-FETCH loading** | **25** (1 migrated in this increment → 24 remaining) | migrate |
| **(b) mutation/submission** | **22** | keep |
| **(c) query-API / prop / type** | **21** | keep |

> The class-(a) count includes thin pass-through wrappers (`use-calendar-days`,
> `use-blog-post-editor`) that re-expose another class-(a) hook's `loading`; they
> migrate transitively when their source hook is converted.

## Class (a) — DATA-FETCH loading (migration candidates)

| File (rel. `frontend/`) | Line(s) | Notes |
|---|---|---|
| `src/modules/knowledge/components/knowledge-base-interface.tsx` | (was 27, 87) | **✅ MIGRATED in this increment** — exemplar, see below. |
| `src/modules/knowledge/hooks/use-documents.ts` | 15 | **✅ MIGRATED** — `useDocuments` now `useSuspenseQuery`. |
| `src/modules/publishing/blog/hooks/use-blog-posts.ts` | 21, 28, 49, 130, 136 | `useEffect` auto-fetch + `setLoading`; mixes data + mutations + filter state (high effort). |
| `src/modules/quality/hooks/use-rubrics.ts` | 16, 21, 31, 72, 78 | `useEffect` auto-fetch + `setLoading`. |
| `src/modules/persona/hooks/use-personas.ts` | 16, 21, 31, 72, 78 | `useEffect` auto-fetch + `setLoading`. |
| `src/modules/editorial/workflow/hooks/use-notifications.ts` | 16, 21, 36, 71 | `useEffect` auto-fetch + `setLoading`. |
| `src/modules/editorial/workflow/hooks/use-workflow-kanban.ts` | 19, 23, 35, 54 | auto-fetch + polling/focus refetch (needs `refetchInterval`). |
| `src/modules/editorial/workflow/hooks/use-content-calendar.ts` | 16, 20, 38, 46 | `useEffect` auto-fetch + `setLoading`. |
| `src/modules/editorial-operations/analytics/hooks/use-editorial-analytics.ts` | 12, 16, 27, 35 | `useEffect` auto-fetch; consumed by 2 pages (dashboard + analytics). |
| `src/modules/publishing/blog/components/version-history-sidebar.tsx` | 25, 28, 39, 56, 59 | self-fetch via `authenticatedFetch` (needs `queryOptions` first). |
| `src/app/dashboard/create/workspace/create-source-materials.tsx` | 41, 59, 73, 139 | mount fetch `loading` (note: `adding` is class b). |
| `src/app/(admin)/admin/users/page.tsx` | 20, 80, 81 | `useEffect`+`fetch('/api/admin/users')`+`setIsLoading`. |
| `src/modules/publishing/distribution/components/regenerate-strategy-section.tsx` | 28, 58 | `isLoading`/`isError` from `useAvailableStrategies` (`isPending` line 161/164 is class b). |
| `src/app/dashboard/create/[id]/page.tsx` | 48, 162 | `isLoading` from `useCarouselProject` → page spinner. |
| `src/app/dashboard/create/[id]/publish/page.tsx` | 44, 131 | `isLoading` from `useCarouselProject` (line 259 `isPending` is class b). |
| `src/app/dashboard/page.tsx` | 28, 30 | `loading` from `useEditorialAnalytics`. |
| `src/app/dashboard/analytics/page.tsx` | 24, 26 | `loading` from `useEditorialAnalytics`. |
| `src/app/dashboard/rubrics/page.tsx` | 15, 61, 66, 71 | `loading` from `useRubrics`. |
| `src/app/dashboard/personas/page.tsx` | 17, 55, 60, 65, 68 | `loading` from `usePersonas`. |
| `src/app/dashboard/workflow/page.tsx` | 35, 54, 59, 71 | `loading` from `useWorkflowKanban`. |
| `src/app/dashboard/calendar/page.tsx` | 16, 32, 37 | `loading` from `useCalendarDays`→`useContentCalendar`. |
| `src/app/dashboard/calendar/use-calendar-days.ts` | 12, 22, 28 | pass-through wrapper of `useContentCalendar`. |
| `src/app/dashboard/blog-posts/page.tsx` | 23, 79, 84, 89 | `loading` from `useBlogPosts`. |
| `src/app/dashboard/blog-posts/[id]/edit/page.tsx` | 31, 45 | `loading` via `use-blog-post-editor`. |
| `src/modules/publishing/blog/hooks/use-blog-post-editor.ts` | 22, 79 | re-exposes `useBlogPosts().loading` (`saving` is class b). |

## Class (b) — Local mutation/submission loading (KEEP)

`use-seo-analysis.ts`, `use-accessibility-check.ts`, `use-blog-ai.ts` (suggest/improve/generateImage/scoreVoice), `use-editorial-workflow.ts` (start/resume), `use-editorial-workflow-resume.ts` (resume/approve/revise), `voice-match-scorer.tsx`, `create-draft-blog-preview.tsx` (button-triggered preview), `login/page.tsx` (`handleSubmit`), `change-password-dialog.tsx`, `edit-user-dialog.tsx`, `delete-user-dialog.tsx`, `create-user-dialog.tsx`, `regenerate-strategy-section.tsx` (`regenerate.isPending`), `blog-post-admin-panel.tsx` (`deleteMutation.isPending`), `file-upload.tsx` (`upload.isPending`), `create/page.tsx` (`createCarousel.isPending`), `create/[id]/publish/page.tsx` (`publishInstagram.isPending`), `ai-suggestion-panel.tsx`, `accessibility-checker.tsx`, `seo-preview.tsx`, `image-gen-modal.tsx`, `create-sidebar.tsx`.

## Class (c) — Query-API wrapper / prop / type-only (NOT a violation)

`use-auth.ts` (re-exposes `useQuery().isPending`), `header.tsx`, `neon-sidebar.tsx` (consume `useAuth().isLoading`), `notification-center.tsx` (prop), `document-list.tsx` (was prop; prop removed in this increment → now class-free), `knowledge/components/types.ts`, `blog/hooks/types.ts`, `editorial/workspace/types.ts`, `editorial/workspace/hooks/types.ts`, `identity/types.ts`, `schemas/neon-button.ts`, `schemas/neon-stat-card.ts`, `neon-button.tsx`, `neon-stat-card.tsx`, `calendar-header.tsx`, `create-workflow-controls.tsx`, `create-workflow-progress.tsx`, `create-materials-gate.tsx`, `brief-step-content.tsx`, `create-workflow-panel.tsx` (presentational `loading` props / type fields).

## Migration safety notes

- **`use-editorial-workflow.ts`** looks like (a) but its `loading` is action
  (start/resume) loading + SSE; the initial `refreshState` does NOT set loading →
  it is class **(b)**. Do **not** Suspense-migrate.
- **`use-workflow-kanban.ts`** adds polling + focus refetch → migrating needs
  `refetchInterval`/`refetchOnWindowFocus` in the query options.
- **`version-history-sidebar.tsx`** / **`create-source-materials.tsx`** use raw
  `authenticatedFetch` (no query layer) → need a `queryOptions` factory before
  Suspense.
- **`use-blog-posts.ts`** mixes data-fetch `loading` with mutations + client-side
  filter state in one hook → split query vs. mutation first. Highest effort.

## Recommended migration order (after this increment)

1. **`useEditorialAnalytics` → `dashboard/page` + `analytics/page`** (2 thin page
   consumers, identical guard branch; convert the hook to `queryOptions` +
   `useSuspenseQuery`).
2. **`useCarouselProject` → `create/[id]/page` + `create/[id]/publish/page`**
   (already a `useQuery` wrapper; clean top-of-component guard).
3. **`useRubrics` / `usePersonas`** (near-identical `useEffect`+`setLoading`
   family; one template covers both).
4. Defer `use-blog-posts`, `use-workflow-kanban`, the raw-`authenticatedFetch`
   components to dedicated tickets (higher effort / extra concerns).

## Exemplar migrated in this increment

**Target:** `src/modules/knowledge/components/knowledge-base-interface.tsx`
(`useDocuments` consumer), chosen as the single safest class-(a) view:

- Lives under `src/app/dashboard/knowledge`, which already has a real,
  error-capable boundary — Next.js segment `error.tsx`
  (`RouteErrorView`) + `loading.tsx`.
- `useDocuments` had exactly **one** consumer, so the change is fully contained
  in the `knowledge` module.

**What changed:**

- `useDocuments` (`hooks/use-documents.ts`): `useQuery(documentsOptions())` →
  `useSuspenseQuery(documentsOptions())`. `data` is now always defined.
- `knowledge-base-interface.tsx`: extracted a `DocumentListSection` that owns the
  read and is wrapped in `<Suspense fallback={<DocumentListSkeleton />}>`. The
  `isLoading` prop is no longer threaded into `DocumentList`.
- `document-list-skeleton.tsx` (new): the former `DocumentList` `isLoading`
  branch markup, verbatim, reused as the Suspense fallback.
- `document-list.tsx` / `types.ts`: removed the now-dead `isLoading` prop/branch.

**Behavior preservation:**

- **Loading UI:** identical — the same three pulsing cards
  (`h-40 animate-pulse rounded-lg bg-[var(--color-muted)]`), now rendered by the
  `<Suspense>` fallback instead of an `if (isLoading)` branch.
- **Data:** identical — same `documentsOptions()` query key + adapter mapping.
- **Error behavior — INTENTIONAL improvement (documented):** previously a fetch
  error was *silently swallowed* (`data` defaulted to `[]` → the empty state
  rendered, hiding the failure). With `useSuspenseQuery` the error now propagates
  to the existing route `error.tsx` (`RouteErrorView`, with a retry button) — the
  ADR-010 declarative error model the boundary was built for. No test asserted
  the old silent-empty path, so this is not a test regression; it is the correct
  surfacing of a previously hidden failure.

**Gates (from `frontend/`):** `npm run test -- --run` 884 passed · `npx tsc
--noEmit` clean · `npx eslint src` 0 errors · `npm run build` passed.

## Remaining scope (deferred — see Note 4 of the ticket)

The "block NEW manual data-fetch loading" **ESLint ratchet rule is NOT shipped in
this increment.** The skeptical review flagged that a naive `no-restricted-syntax`
selector on `isLoading` / `setLoading` is brittle: it cannot, from an AST node
alone, distinguish class (a) from the legitimate classes (b) mutation/submission
flags and (c) `useQuery`-wrapper / prop / type usages — all of which are present
and correct above. A rule that fires on all of them would force `eslint-disable`
churn (forbidden by project policy) and ratchet noise rather than signal.

Precise remaining work for the ratchet:

1. Author a `no-restricted-syntax` selector that targets **only** the (a)
   signature — e.g. a `setLoading`-style `useState` setter called inside a
   `useEffect` whose body also performs a `fetch`/`apiCall` (the class-(a) AST
   shape), explicitly **not** matching `useMutation().isPending`,
   `useQuery`/`useSuspenseQuery` returns, JSX `loading=` props, or type fields.
2. Validate the selector against this baseline: it must flag the 24 remaining
   class-(a) sites and **zero** class-(b)/(c) sites (grandfather the existing 24
   via an allowlist so only *new* violations fail CI — ratchet up, never down).
3. Land the rule in a follow-up ticket once the selector is proven against this
   inventory; do not ship a brittle rule.
