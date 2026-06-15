# `carousel_projects` Field Ownership Map

**Status:** Accepted reference (AE-0105) | **Created:** 2026-06-15 | **Tier:** T2 (Docs/Arch)

**Purpose.** Map every column of the `carousel_projects` table to its invariant, current
writer(s) (with `file:line`), owning context, and concurrency token. This is the
roadmap-mandated prerequisite for **AE-0107** (legacy single write owner for
workflow-owned fields) and **AE-0109** (legacy carousel ACL). No code or schema change —
docs only.

**Source of truth for columns:**
`backend/src/rag_backend/infrastructure/database/models/carousel.py`
(`CarouselProjectModel`, lines 32–294).

> Paths in this document are relative to `backend/src/rag_backend/` unless prefixed.

---

## 1. The five (really seven) writers

The Phase 4 plan names "five distinct writers." Tracing the code, those five logical
writers materialize as the following concrete write sites. The repository, the resume
runner, and the artifact-build service are listed separately because each owns a distinct
slice of fields and a distinct concurrency discipline.

| # | Writer (logical) | Concrete write surface | Persistence mechanism |
|---|------------------|------------------------|-----------------------|
| W1 | **CarouselRepository** (generic CRUD) | `infrastructure/database/carousel_repository.py` — `create_project` (38–44), `update_project` (87–100, via `model.update_from_entity`), `delete_project` (102–114) | `from_entity` / `update_from_entity` + `session.commit()` |
| W2 | **CRUD routes** | `api/routes/carousels/crud.py` — `create_carousel` owner stamp (83–84), `get_carousel` design-token merge (149, response-only), `publish_carousel` (233–246) | direct `model.<field> =` + `session.commit()`, and `repo.update_project` |
| W3 | **Admin routes** | `api/routes/carousels/admin.py` — `refresh_design_tokens` (71–78) | `repo.update_project` + `session.commit()` |
| W4 | **Editorial workflow routes** | `api/routes/carousels/editorial_workflow.py` — `start` (159), `resume` lock bump + `mark_resume_in_progress` (209–216); validate helper `api/routes/carousels/editorial_workflow_routes_validate.py` `bump_resume_lock_version` (208–232) | service calls + `db.commit()` |
| W5a | **Editorial workflow service** | `application/services/carousel/editorial_workflow_service.py` — `_sync_project_phase` (183–211), reviewer assignment (149–151), `mark_resume_in_progress` (347–371) | direct entity-attr writes on a session-attached model + `db.flush()` (commit owned by caller) |
| W5b | **Editorial resume runner** | `application/services/carousel/editorial_workflow_resume_runner.py` — `_revert_background_resume_stuck` (179–182), `_mark_background_resume_failed` (195–198) | direct `project.phase_status =` + `db.commit()` |
| W5c | **Editorial finalize** | `application/services/carousel/editorial_finalize.py` — finalize success (197–202), artifact-health failure (127–128), build failure (152–153) | entity mutation + `repo.update_project` |
| W6 | **Artifact build service / repo** | service `application/services/carousel/artifact_build_service.py` (138, 191, 232 entity-side; `update_project_pdf_paths` 223–236); repo `infrastructure/database/carousel_artifact_build_repository.py` `activate_build` (105–140) — **persisting** writer of `artifact_version` + `lock_version` | compare-and-swap `UPDATE` + `db.commit()` |
| W7 | **Optimistic lock service** | `application/services/optimistic_lock_service.py` — `bump_carousel_version` (75–103) | compare-and-swap `UPDATE ... SET lock_version` |
| W8 | **Image node** (workflow) | `application/services/carousel/nodes/images.py` — `phase_progress` (381–390) | entity mutation + `repo.update_project` |
| Wm | **Phase-5 backfill migration** (one-shot) | `application/services/phase5_migration_service.py` — `_backfill_workflow_state` (251–252) + persona/rubric backfill | direct entity-attr writes + `db.commit()` |

**Read-only access sites (NOT writers, listed to forestall mis-classification):**
`api/dependencies/carousel_access.py` (129/142/158), `api/dependencies/resource_access.py`
(229/263), `api/routes/workflow_board.py` (81), `application/services/content_calendar_service.py`
(56), `application/services/workflow_failure_alert_service.py` (77/121/133/186),
`editorial_workflow_service.get_workflow_state` (338) — all `get`/`select` for read.

> **Note on W5a vs. commit ownership.** `_sync_project_phase` only `flush()`es; the actual
> commit is performed by the route (`editorial_workflow.py:159/216`) or the resume runner.
> For ownership purposes the *field* is owned by W5 (editorial workflow), not by the route
> that happens to flush the transaction.

---

## 2. Column-by-column ownership map

**Owning context legend:** `CRUD` = generic project lifecycle / homepage publish;
`Workflow` = editorial workflow (Phase 4, AE-0107 candidate); `Presentation` = visual
rendering / design (Phase 5+); `Distribution` = blog/LinkedIn/caption fan-out (Phase 5+);
`Identity/ACL` = ownership/visibility (shared, stays at root).

**Classification legend:** **WO** = workflow-owned (Phase 4 / AE-0107 consolidates this
field behind the legacy single write owner); **DEF** = deferred to Phase 5+ (documented
here, left in place). **⚠ MULTI** = written by more than one writer today (AE-0107/0109
consolidation edge case).

### 2.1 Identity / ownership / lifecycle

| Column | Type | Invariant / meaning | Writer(s) `file:line` | Owning context | Class | Rationale |
|--------|------|---------------------|------------------------|----------------|-------|-----------|
| `id` | String(36) PK | Immutable project UUID; LangGraph `thread_id`; checkpoint key | W1 `from_entity` only (model.py:197) | CRUD | DEF | Immutable after create; never updated. Checkpoint-stable (do not rename). |
| `owner_id` | String(36) FK→users | Creator/owner of the project | W1 `update_from_entity` (model.py:282); **W2** `crud.py:83` (stamps `str(user.id)` post-create) | Identity/ACL | DEF | Ownership is an ACL concern (AE-0109/Phase 5), not workflow. ⚠ see §3. |
| `is_public` | Boolean | Public visibility on homepage/blog | W1 (model.py:281); **W2** `crud.py:239,244` (publish) | Identity/ACL | DEF | Public release ≠ workflow approval (split formalized in AE-0111). Visibility = CRUD/ACL. ⚠ see §3. |
| `status` | String(30) | `CarouselStatus` lifecycle (PENDING…COMPLETED/FAILED) | W1 (model.py:268); **W5a** `editorial_workflow_service.py:198` (→FAILED); **W5c** `editorial_finalize.py:199,127,152` (→COMPLETED/mark_failed); Wm `phase5_migration` (read for backfill) | Workflow | **WO** ⚠ | Terminal lifecycle state is driven by the workflow; must move behind editorial owner. ⚠ MULTI: W1+W5a+W5c. |
| `error_message` | Text | Last failure detail | W1 (model.py:269); **W5c** `editorial_finalize.py:127,152` (`mark_failed`); image node failure path `nodes/images.py:275` | Workflow | **WO** ⚠ | Errors are workflow-emitted; consolidate with `status`. ⚠ MULTI. |
| `created_at` | DateTime | Creation timestamp | server_default only (model.py:105) | CRUD | DEF | DB-managed; no app writer. |
| `updated_at` | DateTime | Last-modified timestamp | server `onupdate` + W1 `update_from_entity` (model.py:294) | CRUD | DEF | DB/ORM-managed; bumped on every update by any writer (incidental, not owned). |

### 2.2 Brief / input parameters (set at creation)

| Column | Type | Invariant / meaning | Writer(s) `file:line` | Owning context | Class | Rationale |
|--------|------|---------------------|------------------------|----------------|-------|-----------|
| `topic` | String(500) | Carousel subject | W1 `from_entity` (model.py:198) — create only | Workflow (input) | DEF | Set once at create; not updatable today (absent from `update_from_entity`). Workflow consumes it. |
| `audience` | String(500) | Target audience | W1 create only (model.py:199) | Workflow (input) | DEF | As above; immutable post-create. |
| `niche` | String(200) | Content niche | W1 create only (model.py:200) | Workflow (input) | DEF | As above. |
| `slides_config` | String(200) | Slide count plan (e.g. "1 intro, 3 content…") | W1 create only (model.py:205) | Workflow (input) | DEF | Immutable post-create. |
| `aspect_ratio` | String(20) | Output dimensions (default 1080x1350) | W1 create only (model.py:206) | Presentation (input) | DEF | Immutable post-create; presentation concern. |
| `language` | String(10) | Primary language (default pt-BR) | W1 create only (model.py:207) | Workflow (input) | DEF | Immutable post-create. |
| `generate_images` | Integer (0/1) | Whether to generate images | W1 create only (model.py:208) | Presentation (input) | DEF | Immutable post-create. |
| `image_model` | String(30) | Image backend (gemini default) | W1 create only (model.py:209) | Presentation (input) | DEF | Immutable post-create. |
| `image_style` | String(30) | Visual style (comic_neon default) | W1 create only (model.py:210) | Presentation (input) | DEF | Immutable post-create. |
| `theme` | String(30) | `CarouselTheme` (AUTO default) | W1 create only (model.py:211) | Presentation (input) | DEF | Immutable post-create. |
| `creative_brief` | Text | Workflow creative brief | W1 `update_from_entity` (model.py:275) | Workflow | **WO** | Editorial brief artifact; workflow-owned. |
| `instructions` | Text | Reviewer/author instructions | W1 (model.py:278) | Workflow | **WO** | Editorial input to workflow. |
| `persona_id` | String(36) FK→persona_profiles | Persona applied to content | W1 (model.py:277); Wm `phase5_migration` backfill | Workflow | **WO** ⚠ | Persona drives workflow generation. ⚠ MULTI (W1 + one-shot migration). |
| `rubric_id` | String(36) FK→quality_rubrics | Quality rubric for scoring | W1 `update_from_entity` (model.py:277); Wm backfill | Workflow | **WO** ⚠ | Quality gate input. ⚠ MULTI (W1 + migration). |

### 2.3 Workflow state & concurrency (the Phase 4 core)

| Column | Type | Invariant / meaning | Writer(s) `file:line` | Owning context | Class | Rationale |
|--------|------|---------------------|------------------------|----------------|-------|-----------|
| `current_phase` | String(50) | Active workflow phase (default "brief") | **W5a** `editorial_workflow_service.py:195`; **W2** `crud.py:240,245` (→PHASE_PUBLISHED on publish); Wm `phase5_migration:251` | Workflow | **WO** ⚠ | Phase pointer is the heart of the workflow. ⚠ MULTI: editorial sync vs. CRUD publish stamp vs. migration. |
| `phase_status` | String(50) | Phase sub-state (pending/in_progress/awaiting_human/failed) | **W5a** `editorial_workflow_service.py:196`; **W5b** resume runner `:181,197`; Wm `phase5_migration:252` | Workflow | **WO** ⚠ | Drives interrupt/resume gating. ⚠ MULTI: service vs. background runner vs. migration. |
| `workflow_status` | String(50) | Approval status (e.g. approved_for_publish); gates `publish_carousel` | **W5a** `editorial_workflow_service.py:201` | Workflow | **WO** | Single writer today; the approval token AE-0111 splits from public release. |
| `phase_progress` | JSON | Per-phase progress payload (Kanban/UI) | W1 (model.py:273); **W8** image node `nodes/images.py:381,390` | Workflow | **WO** ⚠ | Workflow progress telemetry. ⚠ MULTI (repo update + image node). |
| `assigned_reviewer_id` | String(36) FK→users | Human reviewer assigned to the workflow | **W5a** `editorial_workflow_service.py:151` (only writer) | Workflow | **WO** | NOT in `update_from_entity` — written *only* via the editorial service. AE-0111 moves assignment behind an editorial port. |
| **`lock_version`** | Integer | **Optimistic-lock concurrency token** (default 1) | **W7** `optimistic_lock_service.py:99` (`bump_carousel_version`, CAS); **W6** `carousel_artifact_build_repository.py:136` (`activate_build`, CAS) | Workflow (concurrency) | **WO** ⚠ | The single concurrency token for the row — see §4. ⚠ MULTI: bumped on two independent CAS paths (resume + artifact activation). |

### 2.4 Presentation / titles / theming (Phase 5+)

| Column | Type | Invariant / meaning | Writer(s) `file:line` | Owning context | Class | Rationale |
|--------|------|---------------------|------------------------|----------------|-------|-----------|
| `title` | String(500) | PT carousel title | W1 `update_from_entity` (model.py:254) | Presentation | DEF | Display copy; presentation slice (Phase 5). |
| `subtitle` | Text | PT subtitle | W1 (model.py:255) | Presentation | DEF | Display copy. |
| `title_en` | String(500) | EN title | W1 (model.py:256) | Presentation | DEF | Display copy (i18n). |
| `subtitle_en` | Text | EN subtitle | W1 (model.py:257) | Presentation | DEF | Display copy (i18n). |
| `primary_color` | String(20) | Brand primary color | W1 (model.py:258) | Presentation | DEF | Theming. |
| `accent_color` | String(20) | Brand accent color | W1 (model.py:259) | Presentation | DEF | Theming. |
| `background_color` | String(20) | Background color | W1 (model.py:260) | Presentation | DEF | Theming. |
| `design_tokens` | JSON | Complete visual design (colors/typography/images/layout) | W1 (model.py:267); **W2** `crud.py:149` (response-merge, not persisted in get); **W3** admin refresh `admin.py:71`; W5c finalize `editorial_finalize.py:201` | Presentation | DEF ⚠ | Visual artifact; Phase 5. ⚠ MULTI: admin refresh + finalize + repo. Left deferred but flagged. |
| `slide_layout_strategy` | String(50) | Layout selection strategy | W1 (model.py:293) | Presentation | DEF | Layout policy; Phase 5. |
| `presentation_policy_version` | String(64) | Presentation policy version applied | W1 (model.py:290) | Presentation | DEF | Policy provenance; Phase 5. |
| `presentation_policy_checksum` | String(80) | Checksum of applied presentation policy | W1 (model.py:291) | Presentation | DEF | Policy provenance; Phase 5. |

### 2.5 Artifacts / output (workflow-produced, presentation-consumed)

| Column | Type | Invariant / meaning | Writer(s) `file:line` | Owning context | Class | Rationale |
|--------|------|---------------------|------------------------|----------------|-------|-----------|
| `output_dir` | String(500) | Root dir for rendered artifacts | W1 `update_from_entity` (model.py:270) | Presentation | DEF | Filesystem artifact location; Phase 5. |
| `pdf_path` | String(500) | PT PDF path | W1 (model.py:271); W6 `artifact_build_service.update_project_pdf_paths:232` (entity) → persisted via finalize `editorial_finalize.py:198,202` | Presentation | DEF ⚠ | Output artifact pointer. ⚠ written via finalize path + generic repo update. |
| `pdf_path_en` | String(500) | EN PDF path | W1 (model.py:272); W6 `artifact_build_service.py:236` (entity) → finalize persist | Presentation | DEF ⚠ | As above. |
| `artifact_version` | String(80) | Active artifact version (CAS-guarded with `lock_version`) | **W6** `carousel_artifact_build_repository.activate_build:135` (**persisting** CAS); entity mirror `artifact_build_service.py:138,191` + `editorial_finalize.py:197` | Workflow/Presentation boundary | DEF ⚠ | Coupled to `lock_version` CAS (§4). Activation is an artifact-publish step (Phase 5 surface) but shares the workflow concurrency token — **AE-0107/0109 must NOT break this CAS pairing.** ⚠ MULTI. |

### 2.6 Distribution / long-form content (Phase 5+)

| Column | Type | Invariant / meaning | Writer(s) `file:line` | Owning context | Class | Rationale |
|--------|------|---------------------|------------------------|----------------|-------|-----------|
| `blog_markdown` | Text | PT blog body | W1 (model.py:261); **W2** publish `crud.py:233`; **W5a** `_sync_project_phase:202-210`; W5c finalize | Distribution | DEF ⚠ | Long-form fan-out; Phase 5. ⚠ MULTI: publish builds-if-missing + workflow sync. |
| `blog_translations` | JSON | Blog body keyed by language | W1 (model.py:262); **W2** publish `crud.py:234` | Distribution | DEF ⚠ | Distribution artifact. ⚠ MULTI. |
| `caption` | Text | PT social caption | W1 (model.py:263); **W5a** `_sync_project_phase:202-210` | Distribution | DEF ⚠ | Distribution copy; synced from workflow state. ⚠ MULTI. |
| `caption_en` | Text | EN social caption | W1 (model.py:264) | Distribution | DEF | Distribution copy. |
| `linkedin_post_pt` | Text | PT LinkedIn post | W1 (model.py:265); **W5a** `_sync_project_phase:202-210` | Distribution | DEF ⚠ | Distribution copy synced from workflow state. ⚠ MULTI. |
| `linkedin_post_en` | Text | EN LinkedIn post | W1 (model.py:266); **W5a** `_sync_project_phase:202-210` | Distribution | DEF ⚠ | As above. ⚠ MULTI. |

### 2.7 Creator watermark metadata (Phase 5+)

| Column | Type | Invariant / meaning | Writer(s) `file:line` | Owning context | Class | Rationale |
|--------|------|---------------------|------------------------|----------------|-------|-----------|
| `creator_name` | String(100) | Creator display name (watermark) | W1 (model.py:283) | Presentation | DEF | Watermark metadata; Phase 5. |
| `creator_handle` | String(100) | Creator handle | W1 (model.py:284) | Presentation | DEF | Watermark metadata. |
| `creator_avatar_url` | String(500) | Creator avatar URL | W1 (model.py:285) | Presentation | DEF | Watermark metadata. |
| `creator_website` | String(500) | Creator website | W1 (model.py:286) | Presentation | DEF | Watermark metadata. |
| `creator_asset_id` | String(36) FK→carousel_creator_assets | Linked creator asset (SET NULL) | W1 (model.py:287-289) | Presentation | DEF | Creator-asset linkage; Phase 5 (creator-assets surface). |

---

## 3. Multi-writer columns (AE-0107 consolidation edge cases)

Every column written by **more than one writer today** — these are the conflicts AE-0107
(single write owner) and AE-0109 (ACL) must resolve. Ordered by priority.

| Column | Writers in conflict | Edge case AE-0107/0109 must resolve |
|--------|---------------------|-------------------------------------|
| `lock_version` | W7 `optimistic_lock_service:99` (resume) **+** W6 `artifact_build_repo:136` (activation) | **Two CAS bump paths.** The single write owner must serialize both so the resume lock and the artifact-activation lock cannot interleave-clobber. Semantics must stay byte-identical (plan §lock_version). |
| `artifact_version` | W6 CAS `:135` (persist) + entity mirrors in service/finalize | Persist path is CAS-paired with `lock_version`; consolidation must keep the pair atomic. |
| `status` | W1 + W5a (→FAILED) + W5c (→COMPLETED/mark_failed) | Terminal-state authority: who decides COMPLETED vs FAILED. Route to one editorial owner. |
| `error_message` | W1 + W5c (`mark_failed`) + image node | Pair with `status`; same owner. |
| `current_phase` | W5a sync `:195` + W2 publish stamp `crud.py:240,245` + Wm migration | CRUD publish sets `PHASE_PUBLISHED` outside the workflow — decide whether publish is a workflow transition or a CRUD overlay. |
| `phase_status` | W5a `:196` + W5b resume runner `:181,197` + Wm | Background runner writes from a *separate session* (`get_session_maker`) — owner must reconcile in-process vs. background mutation. |
| `phase_progress` | W1 + W8 image node `:381,390` | Image node updates progress mid-phase; route through the owner or document as an allowed sub-writer. |
| `design_tokens` | W1 + W3 admin refresh + W5c finalize (+ W2 response-merge, not persisted) | Presentation column (deferred) but multi-written; flagged for Phase 5. |
| `blog_markdown` / `blog_translations` | W1 + W2 publish (build-if-missing) + W5a sync | Distribution columns (deferred); publish vs. workflow authorship overlap. |
| `caption` / `linkedin_post_pt` / `linkedin_post_en` | W1 + W5a sync | Distribution copy synced from workflow state and writable via generic update. |
| `persona_id` / `rubric_id` | W1 + Wm one-shot migration | Migration writer is one-shot/backfill — low risk, but counts as a second writer. |
| `owner_id` | W1 + W2 create-stamp `crud.py:83` | Owner stamped post-create via a second commit; ACL concern (AE-0109). |
| `is_public` | W1 + W2 publish `crud.py:239,244` | Public release flag; AE-0111 splits approval (`workflow_status`) from release (`is_public`). |

**Counts:** 13 multi-writer columns (5 workflow-owned, 8 deferred-but-flagged).

---

## 4. Concurrency token: `lock_version`

- **`lock_version`** (Integer, default 1, NOT NULL — `model.py:88`) is the **single
  optimistic-lock concurrency token** for the `carousel_projects` row.
- **Bumped on two compare-and-swap (CAS) paths today:**
  1. **Resume path** — `optimistic_lock_service.bump_carousel_version`
     (`optimistic_lock_service.py:75-103`): reads current `lock_version`, validates the
     caller's `expected_version`, then `UPDATE ... WHERE id=? AND lock_version=current
     SET lock_version=current+1`; `rowcount != 1` → `ERR_VERSION_CONFLICT`. Invoked from
     the resume route via `bump_resume_lock_version`
     (`editorial_workflow_routes_validate.py:208-232`, called at
     `editorial_workflow.py:209`), surfacing `409 CONFLICT` on contention.
  2. **Artifact-activation path** — `carousel_artifact_build_repository.activate_build`
     (`carousel_artifact_build_repository.py:105-140`): CAS on
     `(lock_version == source_lock_version AND artifact_version == prior_artifact_version)`,
     bumping `lock_version` and setting `artifact_version` atomically; `rowcount != 1` →
     `ERR_ARTIFACT_BUILD_CONFLICT`.
- **Invariant to preserve (plan §"`lock_version` optimistic-lock semantics"):** the
  resume lock-version bump and its concurrent-resume test must stay green; **no
  concurrency-token change** in Phase 4. AE-0107/0111 preserve the bump exactly. Because
  the same token guards both the resume and the artifact-activation CAS, the single write
  owner must keep both paths' semantics byte-identical and must not allow them to bump
  independently in a way that breaks the other's expected-version contract.

---

## 5. Single-write-owner rule & legacy ↔ editorial consistency

### 5.1 Single-write-owner rule (target, AE-0107)

> **Every workflow-owned field of `carousel_projects` SHALL have exactly one write owner.**
> For Phase 4 that owner is the `legacy.carousel_project` single write owner (AE-0107),
> which all workflow writers (W4/W5a/W5b/W5c/W6-lock-bump/W8) route through. Presentation,
> distribution, CRUD-publish, and creator-asset writers (DEF rows above) are **documented
> and left in place** for Phase 5+; they continue to write directly until their owning
> context is extracted.

Concretely, AE-0107 must funnel these **workflow-owned (WO)** columns behind the single
owner: `status`, `error_message`, `current_phase`, `phase_status`, `workflow_status`,
`phase_progress`, `assigned_reviewer_id`, `creative_brief`, `instructions`, `persona_id`,
`rubric_id`, and the `lock_version` concurrency token (with its `artifact_version` CAS
pairing). The multi-writer WO columns in §3 are the consolidation work items.

### 5.2 Legacy-row ↔ editorial-module consistency

- `carousel_projects` **stays one physical table** (god row) through Phase 4 — no split,
  no renames. Editorial does **not** own presentation/blog/distribution columns yet.
- The **legacy carousel ACL** (AE-0109) is the **only** module that translates the legacy
  `carousel_projects` persistence into editorial concepts; editorial handlers must **not**
  import the carousel ORM model directly (epic exit gate, plan §90-101).
- **Retained process-manager note.** The carousel workflow remains the process manager
  driving phase transitions: `_sync_project_phase`
  (`editorial_workflow_service.py:183-211`) keeps the legacy row consistent with LangGraph
  workflow state (`current_phase`/`phase_status`/`workflow_status` + synced distribution
  copy) for the Kanban board. After AE-0107 this sync happens **through** the single write
  owner; the ACL exposes only workflow concepts, never raw columns.
- **Consistency relationship:** the legacy row is the **system of record** for project
  metadata; LangGraph checkpoints (`thread_id = project_id`) are the system of record for
  in-flight workflow execution. The single write owner is responsible for keeping the two
  consistent (idempotent sync), and `lock_version` is the token that detects concurrent
  divergence. Checkpoint identifiers + the `CarouselWorkflowState` schema MUST stay stable
  (plan risk §"LangGraph checkpoint stability").

---

## 6. Sufficiency for AE-0107 / AE-0109 (no unmapped column)

All **53 columns** of `CarouselProjectModel` (`model.py:37-113`, verified by enumeration)
are mapped above with type, invariant, writer(s), owning context, concurrency token, and
class — including the system/DB-managed `id`, `created_at`, `updated_at`. There are **no
unmapped columns**, so the
map is sufficient to scope which fields move behind editorial ports (AE-0107) and which the
ACL must translate (AE-0109): the **WO** rows are in-scope for Phase 4; the **DEF** rows are
explicitly deferred with rationale.

**Summary counts:** 53 columns mapped (all of `CarouselProjectModel`) · 13 multi-writer
columns flagged · **12 workflow-owned (WO)** vs **41 deferred/system/input (DEF)** — 5 of
the 13 multi-writer columns are WO · 1 concurrency token (`lock_version`, bumped on 2 CAS
paths) · 8+ distinct writer surfaces (W1–W8 + one-shot migration Wm).

## 7. References

- ORM model: `backend/src/rag_backend/infrastructure/database/models/carousel.py`
- Phase 4 plan: `docs/plans/phase-4-editorial-carousel.md`
- ADR-009 (Domain Modular Monolith): `docs/decisions/0009-adopt-domain-modular-monolith.md`
- Module conventions: `docs/architecture/module-conventions.md`
- Tickets: `.agent/tasks/AE-0105` (this map), AE-0107 (single write owner), AE-0109 (legacy ACL)
