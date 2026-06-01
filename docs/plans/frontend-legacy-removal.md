# Frontend Legacy Removal Plan (v1.0 → Neon Shell)

**Status:** `accepted`
**Branch:** `design-implementation`
**Related:** [Neon Dashboard Backend Integration](./neon-dashboard-backend-integration.md), [Neon Shell Migration Complete](./neon-shell-migration-complete.md)
**Goal:** Remove all v1.0 dashboard UI, mock data, and orphan components **without changing product behavior**. Business logic stays in `features/*/hooks`; presentation lives under `app/dashboard/**` and the neon design system.

**Non-goal:** Rewriting public blog (`app/(blog)/**`) or admin in this plan unless explicitly scoped.

---

## Executive summary

| Layer | Keep | Remove |
|-------|------|--------|
| Routes | `/dashboard/*` | `/(create)/*`, legacy `/chat`, `/blog-posts`, etc. without redirects |
| Dashboard chat | `app/dashboard/chat/*` + adapters | `ChatInterface`, `features/chat/components/*` UI |
| Dashboard create | `app/dashboard/create/**` + `workspace/*` | `TopicForm`, `features/create/components/*` UI |
| Data | Hooks + API adapters | `mock-data.ts`, static demo constants |
| Shell | `NeonSidebar`, `NeonTopBar` | v1 `Header` editor links to non-existent routes |

Quality is enforced via **Gherkin scenarios**, **Vitest guard tests**, **`npm run check:legacy`**, and a **CI blocking job** (`frontend / Legacy guard`).

---

## Replacement map (behavior preserved)

| Removed surface | Replacement | Hooks / API (unchanged) |
|-----------------|-------------|-------------------------|
| `ChatInterface` | `app/dashboard/chat/page.tsx` + `chat-*.tsx` | `useConversations`, `useCreateConversation`, `useSseChat` |
| `ConversationSidebar` | `ChatSidebar` | `mapConversationToDashboard` |
| `MessageList` / `MessageInput` | `ChatMessageList` / `ChatComposer` | `mapMessageToDashboard` |
| `TopicForm` + `/(create)/create` | `app/dashboard/create/page.tsx` | `useCreateCarousel` |
| `/(create)/create/[id]` workspace | `app/dashboard/create/[id]/page.tsx` | `useCarouselProject`, `useEditorialWorkflow` |
| `/(create)/create/[id]/publish` | `app/dashboard/create/[id]/publish/page.tsx` | `usePublishInstagram`, `PublishPanel` |
| `EditorialWorkflowPanel` | `workspace/create-workflow-panel.tsx` (`CreateWorkflowPanel`) | Same workflow hook |
| `EditorialPhaseReview` | `workspace/create-phase-review.tsx` (`CreatePhaseReview`) | Same |
| `BriefMaterialsGate` | `workspace/create-materials-gate.tsx` (`CreateMaterialsGate`) | Same |
| `SourceMaterialViewer` | `workspace/create-source-materials.tsx` (`CreateSourceMaterials`) | Same |
| `WorkflowKanbanBoard` | `NeonKanbanBoard` on `dashboard/workflow/page.tsx` | `useWorkflowKanban` |
| Static calendar grid | API-only + empty state | `useContentCalendar`, `buildCalendarDaysFromApi` |
| `MOCK_DASHBOARD_*` chat | Live conversation/message streams | `/api/conversations`, SSE chat |

---

## Phase 1 — Dead code & mock inventory (delete only)

### 1.1 Mock and static demo files

| File | Symbols / content | Why removed | Risk if kept |
|------|-------------------|-------------|--------------|
| `src/features/dashboard/chat/mock-data.ts` | `MOCK_DASHBOARD_CONVERSATIONS`, `MOCK_DASHBOARD_MESSAGES` | Hardcoded DeepSeek demo thread; confuses Docker/source reviews | Users see fake chat |
| `src/features/dashboard/blog-posts/mock-data.ts` | `MOCK_BLOG_POSTS` | Unused static list | Dead import temptation |
| `src/app/dashboard/create/constants.ts` | `CREATE_ARTIFACTS`, `CREATE_SUMMARY_ROWS` | Redesign HTML placeholders; never wired | “Dummy” sidebar |
| `src/app/dashboard/rubrics/constants.ts` | `RUBRICS` (`@deprecated`) | Superseded by `useRubrics()` | Duplicate source of truth |
| `src/features/dashboard/chat/constants.ts` | `DASHBOARD_CHAT_ASSISTANT_INTRO`, `_USER_PROMPT`, `_REPLY`, `_FOLLOW_UP` | Only consumed by mock-data | Orphan copy |

**Tests after delete:** `npm run check:legacy-inventory` passes; grep shows zero `MOCK_DASHBOARD` in `src/`.

### 1.2 Legacy chat UI (`features/chat/components/`)

| File | Export | Dependencies | Tests to remove/migrate |
|------|--------|--------------|------------------------|
| `chat-interface.tsx` | `ChatInterface` | `MessageList`, `MessageInput`, `ConversationSidebar`, hooks | `chat-interface.test.tsx` |
| `conversation-sidebar.tsx` | `ConversationSidebar` | `--color-*` styles, `Conversation` type | `conversation-sidebar.test.tsx` |
| `message-list.tsx` | `MessageList` | `MessageItem`, `TypingIndicator` | `message-list.test.tsx` |
| `message-input.tsx` | `MessageInput` | Radix/lucide patterns | `message-input.test.tsx` |
| `message-item.tsx` | `MessageItem` | Legacy bubble layout | `message-item.test.tsx` |
| `typing-indicator.tsx` | `TypingIndicator` | Legacy styles | — |
| `index.ts` | Re-exports above | — | — |

**Keep:** `features/chat/hooks/*`, `features/chat/queries.ts`, `schemas/chat.ts`.

**Guard:** `ChatInterface` must not be imported from any file under `src/app/dashboard/`.

### 1.3 Legacy create UI (`features/create/components/`)

Already removed from working tree; ensure complete deletion:

| File (was) | Export | Replacement |
|------------|--------|-------------|
| `topic-form.tsx` | `TopicForm` | `create-form-sections.tsx` + `create-sidebar.tsx` |
| `editorial-workflow-panel.tsx` | `EditorialWorkflowPanel` | `workspace/create-workflow-panel.tsx` |
| `editorial-phase-review.tsx` | `EditorialPhaseReview` | `workspace/create-phase-review.tsx` |
| `editorial-workflow-progress.tsx` | `EditorialWorkflowProgress` | `workspace/create-workflow-progress.tsx` |
| `editorial-workflow-artifacts.tsx` | `EditorialWorkflowArtifacts` | `workspace/create-workflow-artifacts.tsx` |
| `brief-materials-gate.tsx` | `BriefMaterialsGate` | `workspace/create-materials-gate.tsx` |
| `source-material-viewer.tsx` | `SourceMaterialViewer` | `workspace/create-source-materials.tsx` |
| `workspace-draft-blog-preview.tsx` | `WorkspaceDraftBlogPreview` | `workspace/create-draft-blog-preview.tsx` |
| `carousel-preview.tsx` | `CarouselPreview` | `workspace/create-carousel-preview.tsx` |
| `carousel-progress.tsx` | `CarouselProgress` | `workspace/create-carousel-progress.tsx` |
| `phase-item.tsx` | `PhaseItem` | `workspace/phase-item.tsx` |
| `phase-progress-detail.tsx` | `PhaseProgressDetail` | `workspace/phase-progress-detail.tsx` |
| `slide-progress-grid.tsx` | `SlideProgressGrid` | `workspace/slide-progress-grid.tsx` |
| `progress-icons.tsx` | Icons | `workspace/progress-icons.tsx` |
| `index.ts` | Barrel | Delete or export only hooks pointer comment |

**Keep:** `features/create/hooks/**` only.

### 1.4 Orphan workflow / rubric UI

| File | Export | Replacement | Imported by |
|------|--------|-------------|-------------|
| `features/workflow/components/workflow-kanban-board.tsx` | `WorkflowKanbanBoard` | `NeonKanbanBoard` | **None** |
| `features/workflow/components/content-calendar-view.tsx` | `ContentCalendarView` | `dashboard/calendar/page.tsx` | **None** |
| `features/rubrics/components/rubric-evaluation-panel.tsx` | `RubricEvaluationPanel` | `dashboard/rubrics/rubric-panel.tsx` | **None** |

### 1.5 Legacy App Router group

| Path | Pages | Redirect |
|------|-------|----------|
| `src/app/(create)/create/page.tsx` | TopicForm entry | `/dashboard/create` |
| `src/app/(create)/create/[id]/page.tsx` | Header + chat + workflow | `/dashboard/create/[id]` |
| `src/app/(create)/create/[id]/publish/page.tsx` | Header + publish | `/dashboard/create/[id]/publish` |

Configured in `frontend/next.config.ts` redirects (see Phase 2).

### 1.6 Empty / stub barrels

| File | Action |
|------|--------|
| `src/features/create/components/index.ts` | Delete after Phase 1.3 confirmed |

---

## Phase 2 — Routes & navigation (redirects + link alignment)

### 2.1 Legacy path → dashboard path

| Legacy path | Dashboard path | Notes |
|-------------|----------------|-------|
| `/create` | `/dashboard/create` | In `next.config.ts` |
| `/create/:id` | `/dashboard/create/:id` | In `next.config.ts` |
| `/create/:id/publish` | `/dashboard/create/:id/publish` | In `next.config.ts` |
| `/chat` | `/dashboard/chat` | **Add redirect** |
| `/knowledge` | `/dashboard/knowledge` | **Add redirect** |
| `/personas` | `/dashboard/personas` | **Add redirect** |
| `/rubrics` | `/dashboard/rubrics` | **Add redirect** |
| `/blog-posts` | `/dashboard/blog-posts` | **Add redirect** |
| `/blog-posts/:id/edit` | `/dashboard/blog-posts/:id/edit` | **Add redirect** |
| `/workflow` | `/dashboard/workflow` | **Add redirect** |
| `/calendar` | `/dashboard/calendar` | **Add redirect** |
| `/analytics` | `/dashboard/analytics` | **Add redirect** |

### 2.2 `components/layout/header.tsx` & `mobile-nav.tsx`

Used by **public blog layout** (`app/(blog)/blog/layout.tsx`). Editor links must use `DASHBOARD_ROUTES` or redirects above.

| Current href | Target |
|--------------|--------|
| `/chat` | `/dashboard/chat` |
| `/knowledge` | `/dashboard/knowledge` |
| `/dashboard/create` | OK |
| `/personas` | `/dashboard/personas` |
| `/rubrics` | `/dashboard/rubrics` |
| `/blog-posts` | `/dashboard/blog-posts` |
| `/workflow` | `/dashboard/workflow` |
| `/calendar` | `/dashboard/calendar` |
| `/analytics` | `/dashboard/analytics` |

### 2.3 Constants consolidation

| Constant file | Legacy keys | Action |
|---------------|-------------|--------|
| `constants/api.ts` `ROUTE_PATHS` | `CHAT: "/chat"`, `CREATE: "/create"`, `BLOG_POSTS: "/blog-posts"` | Point editor routes to `/dashboard/*` or alias to `DASHBOARD_ROUTES` |
| `constants/dashboard-routes.ts` | — | **Source of truth** for editor UI |

Update tests: `constants/api.test.ts`, `header.test.tsx`, `blog-post-admin-panel.test.tsx`, `sitemap.ts`.

---

## Phase 3 — Create workspace polish (no API changes)

| Task | Files | Behavior |
|------|-------|----------|
| Rename legacy prop types | `workspace/create-workflow-panel.tsx`, etc. | `EditorialWorkflowPanelProps` → `CreateWorkflowPanelProps` |
| Replace shadcn utility classes | `workspace/*.tsx` | `text-muted-foreground` → neon tokens |
| Wire Generation Report | `create-workspace-sidebar.tsx` | Show `CreateWorkflowArtifacts` / workflow state (not `CREATE_ARTIFACTS`) |
| Commit `(create)` deletion | git | Single conventional commit |

---

## Phase 4 — Dashboard parity (presentation only)

| Page | Issue | Fix (no API change) |
|------|-------|---------------------|
| Calendar | `buildCalendarDays()` mock fallback | Empty state when API returns no items |
| Knowledge | `KnowledgeBaseInterface` + `Container` | Neon shell wrapper; keep hooks |
| Personas / Rubrics | `window.prompt()` | Neon modal forms (same `create` mutations) |
| Chat loading/error | `Container` skeleton | Match neon chat layout |

---

## Phase 5 — Design system consolidation (ongoing)

- Migrate remaining `var(--color-*)` / `text-muted-foreground` in editor features to `@/constants/neon`.
- `globals.css` shadcn semantic tokens may remain for blog/admin until scoped.
- **Do not** reintroduce `components/ui` (shadcn).

---

## Quality enforcement

### Gherkin (spec source of truth)

| Feature file | Scope |
|--------------|--------|
| `tests/features/frontend-legacy-removal.feature` | Dashboard must not use legacy UI; routes resolve to neon shell |
| `tests/features/chat.feature` | Update paths to `/dashboard/chat` |
| `tests/features/header_public_chat.feature` | Update expected hrefs after Phase 2 |
| `tests/features/publish.feature` | Use `/dashboard/create/{id}/publish` |

E2E implementations live in `tests/e2e/` (Playwright). Unit tests reference scenario IDs in comments per project convention.

### Vitest guards

| Test file | Purpose |
|-----------|---------|
| `src/scripts/legacy-removal-guard.test.ts` | Runs `check:legacy` + documents scenario IDs |

### npm scripts

```bash
cd frontend
npm run check:legacy              # Blocking: forbidden imports & routes in app/
npm run check:legacy-inventory    # Blocking: scheduled deletion files must be gone
```

### CI (`Frontend Quality Gates` workflow)

| Job | Command | Enforcement |
|-----|---------|-------------|
| `frontend / Legacy guard` | `npm run check:legacy` | **CI failure** on every PR touching `frontend/**` |
| `frontend / Legacy inventory` | `npm run check:legacy-inventory` | **CI failure** after Phase 1 merge (enable when inventory empty) |

### Pre-merge checklist (PR template / QA agent)

- [ ] `npm run lint && npm run typecheck && npm run test -- --run`
- [ ] `npm run check:legacy` passes
- [ ] `npm run check:legacy-inventory` passes (Phase 1+ PRs)
- [ ] `npm run build` passes
- [ ] No new imports from forbidden modules (see `frontend/scripts/legacy-removal-manifest.json`)
- [ ] Gherkin scenarios for touched flows still pass or are updated
- [ ] E2E: `carousel-editorial-gherkin.spec.ts` uses `/dashboard/create/*`
- [ ] Docker image rebuilt from branch HEAD (not stale `b1ba0c7` mock bundle)

### Stryker / mutation (advisory)

Remove deleted paths from `stryker.conf.json` `mutate` / ignore lists when components are deleted:

- `src/features/chat/components/chat-interface.test.tsx`
- Legacy create component tests (already deleted with files)

---

## Forbidden import manifest

Encoded in `frontend/scripts/legacy-removal-manifest.json` and enforced by `check-legacy-usage.mjs`.

**Must not appear in `src/app/dashboard/**` (imports / JSX / call sites):**

- `ChatInterface`, `TopicForm`
- `WorkflowKanbanBoard`, `ContentCalendarView`, `RubricEvaluationPanel`
- `MOCK_DASHBOARD_CONVERSATIONS`, `MOCK_DASHBOARD_MESSAGES`, `MOCK_BLOG_POSTS`
- `@/features/create/components` (UI barrel)
- `@/components/ui`
- Legacy module paths under `forbiddenLegacyImportPathPrefixes` in `legacy-removal-manifest.json`

**Note:** Renamed workspace files may still contain legacy *type names* (e.g. `BriefMaterialsGateProps`) until Phase 3 rename — the guard targets **usage** of v1 components, not identifier cleanup.

**Must not exist as routes:**

- `src/app/(create)/`

---

## Operational note: Docker / production bundles

A built image may still contain mock strings even after source deletion. **Always rebuild** `alter-ego-frontend` after merge:

```bash
docker compose up -d --build frontend
```

Verify bundle:

```bash
docker exec alter-ego-frontend-1 grep -r "MOCK_DASHBOARD" /app/.next || echo "OK: no mock chat in bundle"
```

---

## Acceptance criteria (plan complete)

| ID | Criterion |
|----|-----------|
| L1 | All Phase 1 files in §1 deleted; `check:legacy-inventory` passes |
| L2 | No `src/app/(create)/` route group |
| L3 | Dashboard chat/create use only `app/dashboard/**` + hooks |
| L4 | Redirects cover all legacy editor paths in §2.1 |
| L5 | `Header` / `mobile-nav` hrefs match dashboard routes |
| L6 | CI `frontend / Legacy guard` green on `main` |
| L7 | Gherkin `frontend-legacy-removal.feature` scenarios implemented in E2E or unit guards |
| L8 | Public blog and admin routes unaffected unless explicitly changed |

---

## Revision history

| Date | Change |
|------|--------|
| 2026-05-29 | Initial plan from codebase scan (mock chat, dummy create, orphan components) |
| 2026-05-29 | YOLO implementation: Phase 1–3 + guards; Phase 4 personas/rubrics modals deferred |
