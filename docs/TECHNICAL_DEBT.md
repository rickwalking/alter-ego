# Technical Debt Backlog

> **Status:** Active backlog
> **When to implement:** After **Phase 5 (Migration & Launch)** is complete
> **Last QA score:** 88/100 (Grade B+) — 2026-05-24 (Phase 5)
> **Source:** Phase 2 QA validation + remediation pass; Phase 3 workflow QA (`/qa-agent`, 2026-05-24)

Items below were identified during Phase 2–3 implementation and QA. They are **not blockers** for Phase 4–5 feature work but should be resolved before declaring the professional pivot production-ready.

---

## Priority Legend

| Priority | Meaning |
|----------|---------|
| P1 | Should fix before production launch |
| P2 | Should fix before scaling / multi-user rollout |
| P3 | Quality polish; schedule when capacity allows |

---

## P1 — Pre-Production

### TD-001: Blog dashboard hook auth consistency

| Field | Value |
|-------|-------|
| **File** | `frontend/src/features/blog/hooks/use-blog-posts.ts` |
| **Issue** | Uses plain `fetch()` instead of `authenticatedFetch`; inconsistent with Phase 2 hooks |
| **Also** | Stale `reviewer_id` query param on approve (`:99`) — backend uses `current_user.id` |
| **Reference** | OWASP A07, QA Security WARN |
| **Acceptance** | All blog CRUD/workflow calls use `authenticatedFetch`; remove dead `reviewer_id` param |

### TD-002: Mutation score below ADR-005 threshold

| Field | Value |
|-------|-------|
| **Estimated score** | ~58% (target: 70%+ on business logic) |
| **Weakest modules** | `carousel_workflow.py` (~38%), `blog_post_ai_service.py` (~52%) |
| **Reference** | [ADR-005](decisions/0005-adopt-mutation-testing.md) |
| **Acceptance** | Incremental `mutmut` on Phase 2 modules ≥ 70%; document surviving mutants |

**Required tests (priority order):**

1. `carousel_workflow.py` — gate routing for all approval fields; non-dict interrupt response
2. `quality_agent.py` — embedding-based originality path (cosine similarity)
3. `blog_post_ai_service.py` — JSON decode fallback in `suggest`; image generation error paths
4. `feedback_learning.py` — `suggest_improvements` ranking; `DRIFT_THRESHOLD` boundary

### TD-003: Phase 2 frontend component & hook tests

| Field | Value |
|-------|-------|
| **Missing tests** | `ai-suggestion-panel`, `image-gen-modal`, `voice-match-scorer`, `rubric-evaluation-panel`, `editorial-workflow-panel`, `source-material-viewer`, `use-blog-ai`, `use-editorial-workflow` |
| **Reference** | TEST-003, Phase 2 UI-011–UI-017 |
| **Acceptance** | Vitest coverage for happy path + error state per component/hook |

### TD-004: Wire or remove Gherkin specs

| Field | Value |
|-------|-------|
| **Files** | `frontend/tests/features/blog_post_editorial.feature`, `carousel_workflow.feature`, `persona_management.feature` |
| **Issue** | Scenarios exist without step definitions / Playwright bindings |
| **Reference** | Gherkin-first rule in `CLAUDE.md` |
| **Acceptance** | Either Playwright step defs implemented OR specs moved to `docs/` as manual test plans |

### TD-017: Admin PUT ownership field mutation

| Field | Value |
|-------|-------|
| **File** | `backend/src/rag_backend/api/dependencies/resource_access.py:93-95`, `blog_post.py:136` |
| **Issue** | Admins can set `author_id` / `reviewer_id` via PUT without `validate_reviewer_user()`, self-review check, or audit event |
| **Reference** | OWASP A01, Phase 3 QA Security WARN |
| **Acceptance** | Reject ownership fields on PUT for all roles (force workflow/assign endpoints) OR validate + audit on admin mutation |

### TD-018: Phase 3 integration test environment

| Field | Value |
|-------|-------|
| **Files** | `tests/integration/test_phase3_workflow.py`, `tests/integration/test_phase1.py` |
| **Issue** | `create_app()` fails in test env with Pinecone import (`cannot import name 'Pinecone'`) — Gherkin scenarios in `phase3_workflow_collaboration.feature` not CI-verifiable |
| **Reference** | Phase 3 QA Acceptance WARN |
| **Acceptance** | Lazy-load or mock `PineconeVectorStore` in tests; Phase 3 integration suite passes in CI |

### TD-019: Phase 3 mutation score below ADR-005 threshold

| Field | Value |
|-------|-------|
| **Estimated score** | ~55% backend weighted (target: 70%+ business logic, 60%+ API routes) |
| **Weakest modules** | `notification_service.py` (~51%), `resource_access.py` (~56%), `optimistic_lock_service.py` (~61%) |
| **Reference** | [ADR-005](decisions/0005-adopt-mutation-testing.md), Phase 3 QA Mutation WARN |
| **Acceptance** | Add Phase 3 modules to `setup.cfg` `paths_to_mutate`; incremental `mutmut` ≥ 60% on API routes |

**Required tests (priority order):**

1. `guard_blog_post_update_fields` — assert non-admin `author_id` / `reviewer_id` stripped from update payload
2. `notification_service.mark_read` — cross-user ownership guard (403/404)
3. `optimistic_lock_service.check_version` — `expected_version is None` early return
4. `optimistic_lock_service.get_active_lock` — expired lock cleanup
5. `resource_access` — admin bypass paths in `get_blog_post_for_read` / `assert_content_access`

### TD-020: Phase 3 frontend workflow wiring

| Field | Value |
|-------|-------|
| **Unused constants** | `WORKFLOW_AUDIT`, `BLOG_VERSIONS` in `frontend/src/constants/workflow.ts` |
| **Missing hooks/actions** | No `useWorkflowAudit`; `use-blog-posts.ts` lacks reject/unpublish; version restore not wired |
| **Files** | `blog-posts/page.tsx`, `version-diff-view.tsx`, `notification-center.tsx` |
| **Reference** | Phase 3 QA Orphan WARN (WF-004, UI-023, UI-022 partial) |
| **Acceptance** | Audit log UI on blog/carousel detail; version history from API; reject/unpublish buttons; notification click navigates via `content_id` / `content_type` |

---

## P2 — Scale & Hardening

### TD-005: Persist feedback learning loop to database

| Field | Value |
|-------|-------|
| **File** | `backend/src/rag_backend/agents/feedback_learning.py:45-69` |
| **Issue** | Corrections stored in in-memory `_corrections`; `session` parameter unused |
| **Reference** | AI-003 completeness, QA Orphan WARN |
| **Acceptance** | `record_correction()` writes to DB; `get_relevant_examples()` reads from DB with embedding search |

### TD-006: Replace in-memory editorial workflow cache

| Field | Value |
|-------|-------|
| **File** | `backend/src/rag_backend/application/services/carousel/editorial_workflow_service.py` |
| **Issue** | Module-level `_WORKFLOW_STATE_CACHE` not safe for multi-worker deployments |
| **Reference** | WF-002 (LangGraph checkpointer), ADR-004 |
| **Acceptance** | Workflow phase state in Redis or LangGraph checkpointer; SSE reads from shared store |

### TD-007: Generic error responses in documents routes

| Field | Value |
|-------|-------|
| **File** | `backend/src/rag_backend/api/routes/documents.py:85,130,379` |
| **Issue** | `detail=f"Failed to read file content: {e!s}"` and `detail=str(e)` leak internals |
| **Reference** | OWASP A10 |
| **Acceptance** | Use constants from `domain/constants/access_control.py` or `api/constants.py`; log details server-side only |

### TD-008: API route integration tests

| Field | Value |
|-------|-------|
| **Missing** | Integration tests for `blog_post_ai.py`, `editorial_workflow.py` (start/resume/SSE), ownership enforcement on blog CRUD |
| **Reference** | AI-005, UI-016, QA Acceptance WARN |
| **Acceptance** | `tests/integration/test_blog_post_ai.py`, `tests/integration/test_editorial_workflow.py` with auth + ownership cases |

### TD-009: Observability test coverage

| Field | Value |
|-------|-------|
| **Missing** | Tests for OBS-003 cross-trace linking, OBS-004 `propagate_attributes`, OBS-006 real Langfuse score attachment |
| **File** | `tests/unit/infrastructure/test_monitoring_langfuse.py` (partial) |
| **Reference** | OBS-001–OBS-006 |
| **Acceptance** | Include `test_monitoring_langfuse.py` in Phase 2 pytest gate; add cross-trace linking test |

### TD-021: Redis event stream consumers

| Field | Value |
|-------|-------|
| **Files** | `domain/constants/workflow_events.py`, `infrastructure/events/redis_stream_publisher.py` |
| **Issue** | `CONSUMER_GROUP_*` and `EVENT_TYPE_NOTIFICATION_CREATED` defined but never used; publisher is write-only; notifications created synchronously in route handlers |
| **Reference** | ADR-004, WF-001, Phase 3 QA Orphan WARN |
| **Acceptance** | Implement `xreadgroup` consumers for workflow + notification groups OR remove unused constants and document publish-only design in ADR |

### TD-022: assign-review draft disclosure scope

| Field | Value |
|-------|-------|
| **Files** | `notifications.py:90-103`, `resource_access.py:279-303` |
| **Issue** | `assign-review` sets `reviewer_id` but does not transition status to `under_review`; assigned reviewer can read full draft immediately |
| **Reference** | OWASP A01, Phase 3 QA Security WARN |
| **Acceptance** | Require `under_review` (or explicit consent flag) before granting reviewer read access; align with submit-for-review flow |

### TD-023: Workflow API payload size limits

| Field | Value |
|-------|-------|
| **Files** | `api/schemas/blog_post.py` (`BlogPostUpdate.content`), `api/schemas/carousel_workflow.py` (`sources` list) |
| **Issue** | Unbounded JSON dict / source list length — DoS vector despite parameterized ORM |
| **Reference** | OWASP A06, Phase 3 QA Security WARN |
| **Acceptance** | Max depth/size on `content`; max list length + per-source size on editorial workflow start schema |

### TD-024: Phase 3 workflow authorization integration tests

| Field | Value |
|-------|-------|
| **Missing** | Unauthorized approve/reject/publish/PUT on another user's post; `POST /blog-posts/{id}/schedule`; content lock API; `GET /workflow-audit/{type}/{id}`; assign-review → notification row created |
| **Files** | `tests/integration/test_phase3_workflow.py`, `backend/tests/features/phase3_workflow_collaboration.feature` |
| **Reference** | Phase 3 QA Acceptance WARN |
| **Acceptance** | Integration tests for IDOR paths (403/404), schedule sets `scheduled_publish_at`, lock acquire/conflict, audit log GET |

### TD-025: Phase 3 frontend component & hook tests

| Field | Value |
|-------|-------|
| **Missing tests** | `notification-center`, `workflow-kanban-board`, `content-calendar-view`, `version-diff-view`, `scheduled-publish-picker`, `review-assignment-panel`, `use-notifications`, `use-workflow-kanban`, `use-content-calendar`, `use-collaborative-edit` |
| **Existing** | `collaborative-lock.test.ts` only (3 tests; missing `currentUserId === null` branch) |
| **Reference** | UI-018–UI-024, Phase 3 QA Acceptance WARN |
| **Acceptance** | Vitest coverage for happy path + error state per component/hook; calendar date-grouping behavior tested |

### TD-026: Blog version history not populated on update

| Field | Value |
|-------|-------|
| **Files** | `api/routes/blog_post_versions.py`, `version-diff-view.tsx` |
| **Issue** | `version_history` only appended on restore, not on normal PUT; `VersionDiffView` compares in-session text, not API history |
| **Reference** | UI-023, Phase 3 QA Orphan WARN |
| **Acceptance** | Append snapshot on each blog PUT; `BLOG_VERSIONS` API drives diff UI |

### TD-027: Kanban board carousel-only scope

| Field | Value |
|-------|-------|
| **File** | `backend/src/rag_backend/api/routes/workflow_board.py:75-79` |
| **Issue** | Board queries only `CarouselProjectModel`; blog posts in editorial workflow absent from `/workflow` |
| **Reference** | UI-018, Phase 3 QA Orphan WARN |
| **Acceptance** | Include blog posts in workflow board OR document carousel-only scope in plan/ADR |

---

## P3 — Polish & Consistency

### TD-010: i18n for AI hook error strings

| Field | Value |
|-------|-------|
| **Files** | `use-blog-ai.ts`, `voice-match-scorer.tsx`, `rubric-evaluation-panel.tsx`, `use-editorial-workflow.ts` |
| **Issue** | Hardcoded English error messages |
| **Reference** | `frontend/CLAUDE.md`, I18N-001 (Phase 4) |
| **Acceptance** | Keys in `en.json` / `pt.json`; `useTranslations` in hooks/components |

### TD-011: Wire `personaId` into blog AI suggestion panel

| Field | Value |
|-------|-------|
| **File** | `frontend/src/app/(dashboard)/blog-posts/page.tsx:252-259` |
| **Issue** | `AiSuggestionPanel` mounted without `personaId`; voice-match branch never runs |
| **Reference** | UI-011 partial |
| **Acceptance** | Persona selector on blog edit form; pass `personaId` to panel |

### TD-012: Consolidate duplicate threshold constants

| Field | Value |
|-------|-------|
| **Files** | `rubrics.py:30` `MIN_PASSING_SCORE`, `domain/constants/persona.py:15` `VOICE_MATCH_MIN_SCORE` |
| **Reference** | CLAUDE.md no magic strings |
| **Acceptance** | Single domain constant; rubrics route imports it |

### TD-013: Strengthen prompt-injection defenses

| Field | Value |
|-------|-------|
| **File** | `backend/src/rag_backend/agents/input_sanitizer.py` |
| **Issue** | Blacklist-only sanitization; bypassable |
| **Reference** | OWASP A05 |
| **Acceptance** | Structured LLM I/O with delimiters; max-length on all workflow schemas; sanitizer as defense-in-depth only |

### TD-014: `documents.py` lint cleanup

| Field | Value |
|-------|-------|
| **File** | `backend/src/rag_backend/api/routes/documents.py` |
| **Rules** | `PLR0913` (line 45), `FBT002` (line 50), `E501` (lines 105, 166) |
| **Acceptance** | `ruff check` clean on file; consider upload request dataclass to reduce arg count |

### TD-015: npm moderate dependency advisories

| Field | Value |
|-------|-------|
| **Status** | 0 high, 5 moderate (transitive via `next-intl`, `@vercel/*`) |
| **Reference** | OWASP A03 |
| **Acceptance** | `npm audit --audit-level=high` clean; moderate resolved or documented with justification |

### TD-016: Unused exports cleanup

| Field | Value |
|-------|-------|
| **Files** | `constants/blog-ai.ts` (`EXPAND`, `EDIT`, `BlogAiAction`); test-only agent methods in `feedback_learning.py`, `quality_agent.py` |
| **Acceptance** | Remove dead exports OR wire to UI; document test-only APIs with `# test-only` marker |

### TD-028: Phase 3 workflow constants cleanup

| Field | Value |
|-------|-------|
| **Files** | `frontend/src/constants/workflow.ts` (`WORKFLOW_PHASES`, `LOCK_CONTENT_TYPE_CAROUSEL` unused); `frontend/src/constants/api.ts:54-57` (duplicate stale Phase 3 entries) |
| **Reference** | Phase 3 QA Orphan WARN, CLAUDE.md no magic strings |
| **Acceptance** | Remove duplicates from `api.ts`; wire or delete unused `workflow.ts` exports |

### TD-029: Collaborative lock UI enforcement

| Field | Value |
|-------|-------|
| **Files** | `blog-post-edit-extras.tsx`, `blog-posts/page.tsx`, `use-collaborative-edit.ts` |
| **Issue** | Lock alert shown but save/edit not disabled when `isLockedByOther`; carousel create path has no lock integration |
| **Reference** | UI-021 partial, Phase 3 QA Orphan WARN |
| **Acceptance** | Disable save when another user holds lock; optionally wire lock to carousel editor |

### TD-030: Workflow hook status constants (frontend)

| Field | Value |
|-------|-------|
| **Files** | `use-notifications.ts` (`"read"` / `"unread"`), `blog-post-edit-extras.tsx` (`"approved"`), `types.ts` (loose `string` for status fields) |
| **Reference** | CLAUDE.md no magic strings, Phase 3 QA Code Quality WARN |
| **Acceptance** | Mirror backend notification/blog status constants in `frontend/src/constants/`; narrow TypeScript unions |

### TD-031: Rate limit key strategy

| Field | Value |
|-------|-------|
| **File** | `backend/src/rag_backend/api/middleware/rate_limiting.py` |
| **Issue** | Limits keyed by IP only (`get_remote_address`); shared egress evades per-user throttling |
| **Reference** | OWASP A06, Phase 3 QA Security WARN |
| **Acceptance** | Composite key (`user_id` + IP) for authenticated workflow endpoints |

### TD-032: Wire Phase 3 Gherkin feature file

| Field | Value |
|-------|-------|
| **File** | `backend/tests/features/phase3_workflow_collaboration.feature` |
| **Issue** | 6 scenarios; collaborative-lock scenario referenced in frontend test comment but absent from feature file; several scenarios only partially mapped |
| **Reference** | Gherkin-first rule, Phase 3 QA Acceptance WARN |
| **Acceptance** | Add missing scenarios (audit, lock, schedule API, reject path); align integration tests with feature file |

---

## Architectural Decisions Deferred

These are **intentional** for single-tenant MVP; revisit if multi-tenancy or spec fidelity is required.

| ID | Topic | Current behavior | Trigger to revisit |
|----|-------|------------------|-------------------|
| TD-A01 | Carousel public list | `list_carousels` allows unauthenticated read | Public gallery product requirement |
| TD-A02 | Personas/rubrics global | Any editor can CRUD any persona/rubric | Multi-tenant / per-team isolation |
| TD-A03 | Phase 1 TipTap editor | Blog editor uses Textarea, not rich text | UI-006 completion in Phase 1 backlog |
| TD-A04 | UI-021 collaborative editing | TTL content locks + polling (`use-collaborative-edit.ts`), not Yjs/Liveblocks | Real-time multi-cursor editing required |
| TD-A05 | NOTIF-001 email delivery | `_send_email` logs via `logger.info`; sets `email_sent=True` — no SMTP/provider | Production email notifications required |
| TD-A06 | WF-001 event transport | Redis Streams only (no Kafka) | Kafka mandated by ops / ADR change |
| TD-A07 | Carousel reviewer assignment | `assign-review` returns `400 reviewer_assignment_unsupported` for carousels | Carousel editorial review workflow product scope |
| TD-A08 | assign-review pre-submit read | Reviewer can read draft after assignment without `under_review` status | Stricter confidentiality / compliance requirement |

---

## Phase 4 Items Deferred (from pivot plan + QA)

Carried forward from Phase 4 QA (2026-05-24):

| ID | Priority | Summary |
|----|----------|---------|
| TD-033 | P1 | Frontend plagiarism check UI — API exists, no component |
| TD-034 | P1 | Frontend AI disclosure badge — API exists, no UI |
| TD-035 | P2 | `BlogPostRepository` loads full ORM rows — no column deferral for listings |
| TD-036 | P2 | CDN wired for blog AI images only; `resolve_carousel_image()` unused |
| TD-037 | P1 | Phase 4 frontend Vitest tests (SEO, a11y, filters, shortcuts, analytics) |
| TD-038 | P1 | Phase 4 integration tests — 5/7 Gherkin scenarios not CI-verified |
| TD-039 | P2 | Middleware editor-role gate for `/blog-posts`, `/analytics` (API enforces `EditorUser`) |
| TD-040 | P3 | OpenTelemetry span constants unused; partial service coverage |
| TD-041 | P3 | Quality routes use `dict[str, object]` + `# type: ignore[arg-type]` (mypy strict debt) |
| TD-042 | P3 | `onAiSuggest` keyboard shortcut not wired in blog-posts page |
| TD-043 | P3 | Pagination UI not exposed (hook has `total`/`offset` but no UI controls) |

### TD-033: Frontend plagiarism check UI

| Field | Value |
|-------|-------|
| **API** | `POST /api/blog-posts/{id}/plagiarism-check` |
| **Issue** | Backend `PlagiarismDetectionService` implemented; no dashboard component |
| **Reference** | QUAL-001, Phase 4 QA Acceptance WARN |
| **Acceptance** | Panel on blog edit view; shows similarity score + flagged passages |

### TD-034: Frontend AI disclosure badge

| Field | Value |
|-------|-------|
| **API** | `ai_disclosure_label` on blog post; enforced at publish |
| **Issue** | No badge/picker in blog editor UI |
| **Reference** | QUAL-002, Phase 4 QA Orphan WARN |
| **Acceptance** | Disclosure selector + published badge on blog post view |

### TD-035: Blog listing query optimization (column deferral)

| Field | Value |
|-------|-------|
| **File** | `backend/src/rag_backend/infrastructure/database/blog_post_repository.py` |
| **Issue** | Summary endpoint still loads full ORM rows; no `defer()` on heavy JSON columns |
| **Reference** | PERF-001 partial, Phase 4 QA Code Quality WARN |
| **Acceptance** | List query defers `content`, `version_history`, `ai_suggestions` columns |

### TD-036: CDN integration for carousel images

| Field | Value |
|-------|-------|
| **File** | `backend/src/rag_backend/application/services/asset_cdn_service.py` |
| **Issue** | `resolve_carousel_image()` defined but not wired to carousel routes |
| **Reference** | PERF-002 partial |
| **Acceptance** | Carousel slide/image URLs rewritten when `cdn_enabled=true` |

### TD-037: Phase 4 frontend component & hook tests

| Field | Value |
|-------|-------|
| **Missing tests** | `seo-preview`, `accessibility-checker`, `blog-post-filters`, `keyboard-shortcuts-help`, `use-seo-analysis`, `use-accessibility-check`, `use-editorial-analytics`, `use-editor-shortcuts`, analytics page |
| **Reference** | UI-025–UI-030, Phase 4 QA Acceptance WARN |
| **Acceptance** | Vitest coverage for happy path + error state per component/hook |

### TD-038: Phase 4 integration test coverage

| Field | Value |
|-------|-------|
| **File** | `backend/tests/features/phase4_quality_polish.feature` |
| **Issue** | Only SEO + analytics scenarios have integration tests; accessibility, plagiarism, disclosure, audit, list pagination missing |
| **Reference** | Phase 4 QA Acceptance WARN, TD-018 (Pinecone env) |
| **Acceptance** | Integration tests for all 7 Gherkin scenarios pass in CI |

### TD-039: Frontend middleware editor-role gate

| Field | Value |
|-------|-------|
| **Files** | `frontend/src/constants/middleware.ts`, dashboard routes |
| **Issue** | `/blog-posts`, `/analytics` accessible to any authenticated user at UI layer |
| **Reference** | OWASP A01, Phase 4 QA Security WARN |
| **Acceptance** | Middleware redirects non-editors; aligns with backend `EditorUser` |

### TD-040: OpenTelemetry instrumentation gaps

| Field | Value |
|-------|-------|
| **Files** | `infrastructure/telemetry/opentelemetry.py`, quality/workflow services |
| **Issue** | Span name constants defined but unused; not all Phase 4 services instrumented |
| **Reference** | MON-001 partial |
| **Acceptance** | Spans on plagiarism, SEO, a11y, editorial audit services; constants wired |

### TD-041: Quality route type safety

| Field | Value |
|-------|-------|
| **File** | `backend/src/rag_backend/api/routes/blog_post_quality.py` |
| **Issue** | `dict[str, object]` casts with `# type: ignore[arg-type]` for design colors |
| **Reference** | `backend/AGENTS.md` mypy strict |
| **Acceptance** | TypedDict or Pydantic schema for design colors; zero type ignores |

### TD-042: Keyboard shortcut `onAiSuggest` unwired

| Field | Value |
|-------|-------|
| **File** | `frontend/src/app/(dashboard)/blog-posts/page.tsx` |
| **Issue** | `useEditorShortcuts` accepts `onAiSuggest` but page does not pass handler |
| **Reference** | UI-030 partial |
| **Acceptance** | Shortcut opens AI suggestion panel on blog edit view |

### TD-043: Blog post list pagination UI

| Field | Value |
|-------|-------|
| **Files** | `use-blog-posts.ts`, `blog-posts/page.tsx` |
| **Issue** | Hook exposes `total`/`offset`/`limit` but page renders all loaded items without pager |
| **Reference** | PERF-001, UI-028 partial |
| **Acceptance** | Prev/next or page controls; fetches with offset |

**Note:** TD-001 (`authenticatedFetch` in `use-blog-posts.ts`) was **partially addressed** during Phase 4 QA fixes — verify remaining CRUD/workflow calls and close when complete.

---

## Phase 3 Items Deferred (from pivot plan + QA)

Carried forward from Phase 3 QA (2026-05-24) — tracked as TD-017–TD-032 above; summary by criterion:

| ID | Criterion | Gap | Debt item |
|----|-----------|-----|-----------|
| UI-021 | Collaborative editing (Yjs/Liveblocks) | Lock-based polling only | TD-A04, TD-029 |
| NOTIF-001 | Email notifications | Log-only, no SMTP | TD-A05 |
| WF-001 | Kafka/Redis event bus | Redis Streams publish-only | TD-A06, TD-021 |
| UI-023 | Version diff view | Local session diff; API unwired | TD-020, TD-026 |
| UI-019/024 | Notification center / schedule picker | No Vitest coverage | TD-025 |
| UI-018 | Kanban board | Blog posts excluded | TD-027 |
| WF-004 | Workflow audit log | Backend only; no frontend UI | TD-020 |
| — | Integration test CI | Pinecone import blocks `create_app()` | TD-018 |

---

## Phase 1 Items Still Open (from pivot plan)

Carried forward — not Phase 2 scope but tracked for completeness:

- **UI-006**: TipTap rich text editor for blog posts
- **UI-007**: Editorial comment thread component
- **UI-008**: Version history sidebar with diff view
- **UI-009**: Project creation form (brief, persona, rubric, sources)
- **UI-010**: AI suggestion tooltip for editor
- **TEST-003**: Component tests for Phase 1 UI
- **TEST-004**: E2E tests for blog post creation workflow

---

## Implementation Order (Suggested)

After Phase 5 launch tasks (`MIG-*`, `DEPLOY-*`):

1. **TD-001** → **TD-003** → **TD-004** → **TD-032** (frontend consistency + Gherkin)
2. **TD-018** → **TD-024** (Phase 3 integration tests unblocked + expanded)
3. **TD-002** → **TD-019** (mutation score — unblocks CI quality gate)
4. **TD-020** → **TD-026** → **TD-029** (Phase 3 frontend wiring)
5. **TD-005** → **TD-006** → **TD-021** (persistence + event consumers for production scale)
6. **TD-017** → **TD-022** → **TD-023** → **TD-031** (security hardening batch)
7. **TD-007** → **TD-008** → **TD-009** (Phase 2 security + observability)
8. **TD-025** → **TD-028** → **TD-030** (Phase 3 tests + constants polish)
9. **TD-010** → **TD-016** (Phase 2 polish batch)
10. **TD-033** → **TD-043** (Phase 4 deferred items — see Phase 4 section above)

---

## Tracking

When starting an item, add the ID to the commit scope (e.g. `fix(debt): TD-001 migrate use-blog-posts to authenticatedFetch`).

Update this file status when an item is completed: change row to ✅ with completion date and PR reference.
