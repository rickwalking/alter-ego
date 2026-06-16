# Presentation Surface Ownership Map (Phase 5)

**Status:** Accepted reference (AE-0115) | **Created:** 2026-06-15 | **Tier:** T2 (Docs/Arch)

**Purpose.** Map the **presentation** surface of the carousel god object for Phase 5: every
presentation `carousel_projects` column **and** every `CarouselSlideModel` column to its
type, current writer(s) (`file:line`), presentation-owned vs deferred classification, and
multi-writer flags. Document the `artifact_version`↔`lock_version` compare-and-swap (CAS)
pairing and the **shared-owner coordination requirement** it imposes, and map the
**editorial↔presentation call boundary** (the port surface). This is the prerequisite for
**AE-0118** (presentation ACL + no-clobber concurrency), **AE-0120** (presentation facade /
read serving), and **AE-0121** (editorial→presentation port).

> Extends the AE-0105 map (`docs/architecture/carousel-project-field-ownership.md`). That
> map classified the presentation columns as **DEF** (deferred to Phase 5); this document
> is the deferred detail it pointed at. Paths are relative to `backend/src/rag_backend/`
> unless prefixed. Behavior-preserving phase — **no renames, no schema change** (later
> phases); the activation CAS and response bytes (design/slide/strategy JSON, PDF/JPEG
> `FileResponse`) stay byte-identical.

**Source of truth for columns:**
`backend/src/rag_backend/infrastructure/database/models/carousel.py`
(`CarouselProjectModel` lines 32–119; `CarouselSlideModel` lines 303–390).

---

## 1. Presentation writers (concrete write surfaces)

The presentation surface is written by these concrete sites. Like AE-0105, the
"entity-side" writers mutate an in-memory `CarouselProject`/`CarouselSlide` that is later
persisted by a generic repo writer; the **persisting** writer is named where it differs.

| # | Writer (logical) | Concrete write surface | Mechanism |
|---|------------------|------------------------|-----------|
| P1 | **CarouselRepository** (generic CRUD persist) | `infrastructure/database/carousel_repository.py` — `update_project` (87–100, via `model.update_from_entity` model.py:258–300), `update_slide` (136–147, via `CarouselSlideModel.update_from_entity` model.py:379–390), `create_slide` (116–124) | `from/update_from_entity` + `commit()` |
| P2 | **Admin refresh-design-tokens** | `api/routes/carousels/admin.py` — `refresh_design_tokens` (71 sets `design_tokens`, 72 `repo.update_project`, 78 `session.commit()`) | entity write → P1 persist + commit |
| P3 | **Design node** (workflow) | `application/services/carousel/nodes/design.py` — `run_design` (51–55 `set_theme_colors` → `primary/accent/background_color`; 57 `design_tokens`) — **entity-side**, persisted later by P1 | entity mutation |
| P4 | **Export node** (workflow) | `application/services/carousel/nodes/export.py` — `render_language` (117 `pdf_path_en`, 119 `pdf_path`) — **entity-side**, persisted by finalize/P1 | entity mutation |
| P5 | **Image node** (workflow) | `application/services/carousel/nodes/images.py` — `_publish_progress_state` (381–390 `phase_progress` + `repo.update_project`); `_persist_slide_image` (285 slide `image_path`, 286–293 `_apply_image_metadata` → slide `metadata`, 294 `repo.update_slide`) | entity mutation + P1 persist |
| P6 | **Artifact build service / repo** | service `artifact_build_service.py` — `build_and_activate` (138 entity mirror `artifact_version`, 191 `_activate_existing` mirror), `update_project_pdf_paths` (223–236 entity `pdf_path`/`pdf_path_en`); repo `carousel_artifact_build_repository.py` — `activate_build` (105–165, **persisting CAS** `UPDATE` at 127–138 sets `artifact_version` + `lock_version`) | CAS `UPDATE` + `commit()` |
| P7 | **Editorial finalize** (terminal write) | `editorial_finalize.py` — `export_and_complete_carousel` (197 entity `artifact_version`, 198 `update_project_pdf_paths`, 209 `design_tokens = merge_design_tokens_with_disk`, 210 `repo.update_project`); `_try_build_artifacts` (139 calls P6 `build_and_activate`) | entity mutation → P1 persist (atomic with WO `status`) |
| P8 | **Content-drafting slide persist** | `editorial_distribution_persist.py` — `_apply_draft_to_existing_slide` (110 `heading`, 111 `body`, 112 `image_prompt`, 113 `extras`, 114 `metadata`, 115 `image_path=None`, 116 `update_slide`); `_create_slide_from_outline_item` (152–162 `create_slide`) | entity write → P1 persist |
| P9 | **Refinement service** (slide prompt rewrite) | `carousel_refinement.py` — `refine_image_prompt` (165 slide `image_prompt`, 166–168 `extras`, 169 `update_slide`); `refinement_service.re_render_slides` (called by P7) | entity write → P1 persist |
| P10 | **Visual pipeline** (slide create) | `editorial_visual_pipeline.py` — `create_slide` (84) | P1 persist |

**Read-only presentation access (NOT writers):** `crud.py` `get_carousel` (149,
`merge_design_tokens_with_disk`, **response-only** — see §6) and `list` responses;
`artifact_build_service.read_project_lock_version` (212–220, read). These do not persist.

> **Persist-path note.** P3/P4/P7/P8/P9 mutate the entity; `CarouselProjectModel.update_from_entity`
> (model.py:258–300) writes **all** presentation columns on every `update_project`, and
> `CarouselSlideModel.update_from_entity` (model.py:379–390) writes all slide columns on
> every `update_slide`. So any caller that mutates one presentation field and calls
> `update_project`/`update_slide` re-stamps the whole row from the entity — an
> over-write hazard AE-0118's ACL must account for (last-writer-wins on unrelated columns).

---

## 2. Presentation `carousel_projects` columns

**Legend.** Class: **PO** = presentation-owned (moves behind the presentation ACL/facade in
AE-0118/0120); **DEF** = deferred-within-presentation (no extraction action needed beyond
documentation — input-only or write-once); **⚠ MULTI** = written by >1 writer today
(consolidation edge case for AE-0118, see §4). Type from `models/carousel.py`.

### 2.1 Titles / theming / design (presentation-owned)

| Column | Type | Meaning | Writer(s) `file:line` | Class |
|--------|------|---------|------------------------|-------|
| `title` | String(500) null | PT carousel title | P1 `update_from_entity` (model.py:260) | PO |
| `subtitle` | Text null | PT subtitle | P1 (model.py:261) | PO |
| `title_en` | String(500) null | EN title (i18n) | P1 (model.py:262) | PO |
| `subtitle_en` | Text null | EN subtitle (i18n) | P1 (model.py:263) | PO |
| `primary_color` | String(20) null | Brand primary color | P1 (model.py:264); **P3** design node `nodes/design.py:51-55` (`set_theme_colors`) | PO ⚠ |
| `accent_color` | String(20) null | Brand accent color | P1 (model.py:265); **P3** `nodes/design.py:51-55` | PO ⚠ |
| `background_color` | String(20) null | Background color | P1 (model.py:266); **P3** `nodes/design.py:51-55` | PO ⚠ |
| `design_tokens` | JSON null | Complete visual design (colors/typography/images/layout) | P1 (model.py:273); **P2** admin refresh `admin.py:71`; **P7** finalize `editorial_finalize.py:209`; (P? `crud.py:149` response-only, **not persisted** — §6) | PO ⚠ |
| `slide_layout_strategy` | String(50) null | Layout selection strategy | P1 (model.py:299) | PO |
| `presentation_policy_version` | String(64) null | Presentation policy version applied | P1 (model.py:296) | PO |
| `presentation_policy_checksum` | String(80) null | Checksum of applied presentation policy | P1 (model.py:297) | PO |

### 2.2 Artifacts / output (presentation-owned; CAS boundary)

| Column | Type | Meaning | Writer(s) `file:line` | Class |
|--------|------|---------|------------------------|-------|
| `output_dir` | String(500) null | Root dir for rendered artifacts | P1 `update_from_entity` (model.py:276) | PO |
| `pdf_path` | String(500) null | PT PDF path | P1 (model.py:277); **P4** export node `nodes/export.py:119`; **P6** `artifact_build_service.update_project_pdf_paths:232`; **P7** finalize `editorial_finalize.py:198` | PO ⚠ |
| `pdf_path_en` | String(500) null | EN PDF path | P1 (model.py:278); **P4** `nodes/export.py:117`; **P6** `artifact_build_service.py:236`; **P7** finalize `editorial_finalize.py:198` | PO ⚠ |
| `artifact_version` | String(80) null | Active artifact version (**CAS-guarded with `lock_version`** — §3) | **P6** `carousel_artifact_build_repository.activate_build:135` (**persisting CAS**); entity mirrors `artifact_build_service.py:138,191`; **P7** finalize `editorial_finalize.py:197` | PO ⚠ |

### 2.3 Creator watermark metadata (presentation-owned)

| Column | Type | Meaning | Writer(s) `file:line` | Class |
|--------|------|---------|------------------------|-------|
| `creator_name` | String(100) null | Creator display name (watermark) | P1 (model.py:289) | PO |
| `creator_handle` | String(100) null | Creator handle | P1 (model.py:290) | PO |
| `creator_avatar_url` | String(500) null | Creator avatar URL | P1 (model.py:291) | PO |
| `creator_website` | String(500) null | Creator website | P1 (model.py:292) | PO |
| `creator_asset_id` | String(36) FK→carousel_creator_assets (SET NULL) | Linked creator asset | P1 (model.py:293-295) | PO |

### 2.4 Presentation input parameters (set at create; write-once)

These are presentation-context inputs but are **create-only** (absent from
`update_from_entity`), so they are **DEF** — no ongoing writer, no consolidation work.

| Column | Type | Meaning | Writer `file:line` | Class |
|--------|------|---------|--------------------|-------|
| `aspect_ratio` | String(20) | Output dimensions (default 1080x1350) | P1 `from_entity` create only (model.py:52 / from_entity) | DEF |
| `generate_images` | Integer (0/1) | Whether to generate images | P1 create only (model.py:54) | DEF |
| `image_model` | String(30) | Image backend (gemini default) | P1 create only (model.py:55) | DEF |
| `image_style` | String(30) | Visual style (comic_neon default) | P1 create only (model.py:56) | DEF |
| `theme` | String(30) | `CarouselTheme` (AUTO default) | P1 create only (model.py:57) | DEF |

---

## 3. `artifact_version` ↔ `lock_version` compare-and-swap pairing

`lock_version` (Integer, default 1, NOT NULL — model.py:94) is the **single optimistic-lock
concurrency token** for the `carousel_projects` row. It is **shared** between two
independent CAS paths that bump it:

1. **Editorial resume CAS (AE-0107)** —
   `application/services/optimistic_lock_service.py` `bump_carousel_version` (75–103):
   `UPDATE ... WHERE id=? AND lock_version=current SET lock_version=current+1`;
   `rowcount != 1` → `ERR_VERSION_CONFLICT`. Invoked through the editorial single write
   owner `modules/editorial/infrastructure/carousel_project_write_owner.py`
   `bump_resume_lock_version` (129–147), which delegates **unchanged** to
   `OptimisticLockService.bump_carousel_version`.

2. **Presentation artifact-activation CAS (this surface)** —
   `infrastructure/database/carousel_artifact_build_repository.py` `activate_build`
   (105–165). It reads current `lock_version` + `artifact_version` (116–124), then the
   **persisting CAS** `UPDATE` (127–138):
   `WHERE id=? AND lock_version=source_lock_version AND artifact_version=prior_artifact_version
   SET artifact_version=<new>, lock_version=current+1`; `rowcount != 1` →
   `ERR_ARTIFACT_BUILD_CONFLICT`. Driven by `CarouselArtifactBuildService.build_and_activate`
   (`artifact_build_service.py:129-137`), whose `source_lock_version` comes from
   `read_project_lock_version` (212–220) at finalize time (`editorial_finalize.py:137`).

**The pairing.** The presentation activation CAS does **not** bump `lock_version` alone — it
bumps it **atomically together with** `artifact_version`, and its guard is the *compound*
predicate `(lock_version == source AND artifact_version == prior)`. So `artifact_version` is
the presentation payload and `lock_version` is the shared row token; they move as one atomic
unit. This is the **invariant AE-0118/0121 SHALL preserve exactly** — byte-identical CAS
predicate, compound guard, and the `+1` bump.

### 3.1 SHARED-owner coordination requirement (for AE-0118)

Because **one** `lock_version` token guards **both** the editorial resume bump and the
presentation activation bump, the two owners are **coupled** on a shared primitive:

- The editorial AE-0107 owner (`carousel_project_write_owner.py`) and the presentation
  activation path (`activate_build`) **both** increment `lock_version`. Neither may treat
  it as private.
- **Requirement:** there SHALL be a **single shared CAS primitive** (or an enforced
  serialization point) over `lock_version`. AE-0118 SHALL implement the presentation owner
  so that an activation bump and a concurrent resume bump cannot interleave-clobber: each
  reads the current version, validates its expected/source version, and the loser gets a
  conflict (`ERR_ARTIFACT_BUILD_CONFLICT` / `ERR_VERSION_CONFLICT`) — **never** a silent
  overwrite. The expected-version contract of *each* path must remain valid in the presence
  of the other (a resume bump invalidates a stale `source_lock_version` held by an
  in-flight activation, and vice-versa).
- **Testability (no-clobber concurrency):** AE-0118 SHALL have a test that interleaves a
  resume bump and an activation bump against the same row and asserts exactly one succeeds,
  the other returns its conflict error, and `lock_version` advances by exactly one per
  successful bump (no lost update).

> Carryover from AE-0105 §4: this is the same "two CAS bump paths" item flagged for
> workflow consolidation. Phase 5 re-states it as the **cross-owner** coordination contract
> the presentation ACL inherits.

---

## 4. Multi-writer presentation columns / slide fields (consolidation edge cases)

Every presentation column or slide field written by **more than one writer** today. These
are the conflicts AE-0118's presentation ACL must serialize / route through one owner.

| Field | Writers in conflict | Edge case AE-0118 must resolve |
|-------|---------------------|--------------------------------|
| `lock_version` | resume CAS `optimistic_lock_service.py:99` **+** activation CAS `carousel_artifact_build_repository.py:136` | Shared token — single CAS primitive / serialization (§3.1). |
| `artifact_version` | P6 CAS `:135` (persist) + entity mirrors `artifact_build_service.py:138,191` + P7 `editorial_finalize.py:197` | Persist path is CAS-paired with `lock_version`; the entity mirrors/finalize write must not race the CAS. Keep the pair atomic. |
| `design_tokens` | P1 + P2 admin refresh `admin.py:71` + P7 finalize `editorial_finalize.py:209` (+ `crud.py:149` response-only, **not persisted**) | Three persist paths: workflow finalize vs admin bulk refresh vs generic update. Route through the presentation owner. |
| `pdf_path` | P1 + P4 `nodes/export.py:119` + P6 `update_project_pdf_paths:232` + P7 `editorial_finalize.py:198` | Output pointer set by export node, artifact resolver, and finalize. One owner. |
| `pdf_path_en` | P1 + P4 `nodes/export.py:117` + P6 `:236` + P7 `editorial_finalize.py:198` | As above. |
| `primary_color` / `accent_color` / `background_color` | P1 + P3 design node `nodes/design.py:51-55` | Design node stamps colors mid-render; generic update also writes them. |
| **slide** `image_path` | P5 image node `nodes/images.py:285` + P8 draft persist `editorial_distribution_persist.py:115` (reset to None) + P1 `update_from_entity` | Image node sets the path; draft re-apply resets it to None. Order-sensitive. |
| **slide** `image_prompt` | P8 `editorial_distribution_persist.py:112` + P9 refinement `carousel_refinement.py:165` | Drafting sets initial prompt; refinement rewrites it (also into `extras`). |
| **slide** `extras` | P8 `editorial_distribution_persist.py:113` + P9 `carousel_refinement.py:166-168` | `image_prompt` duplicated into `extras` by both — keep consistent. |
| **slide** `heading` / `body` | P8 `editorial_distribution_persist.py:110,111` + P1 `update_from_entity` | Content drafting authors them; generic update re-stamps. |

**Note on `phase_progress`.** Written by the image node (`nodes/images.py:381-390`) and the
repo (model.py:279). It is classified **workflow-owned** in AE-0105 (§2.3), not presentation
— the image node's `phase_progress` write is the **presentation→editorial callback** (§5.3),
not a presentation column. It is listed here only to disambiguate.

---

## 5. Editorial ↔ presentation call boundary (the port surface for AE-0121)

The presentation operations are invoked **from** the editorial workflow today; AE-0121 turns
these call sites into an editorial→presentation **port**. The boundary has two directions.

### 5.1 Editorial → presentation (forward calls)

| Boundary call | Site | What it invokes |
|---------------|------|------------------|
| **Finalize → artifact build** | `editorial_finalize.py` — `_try_build_artifacts` (139) calls `CarouselArtifactBuildService().build_and_activate`; terminal persist (197–210, atomic with WO `status`/`error_message` — see comment 199–206) | Stage → manifest → promote → **activation CAS** (§3) + PDF-path + design-token merge |
| **Design node** | `application/services/carousel/nodes/design.py` — `run_design` (40–84) | Resolve theme, stamp `design_tokens` + colors, build PT HTML |
| **Images node** | `application/services/carousel/nodes/images.py` — `run_images` (469–491) / `run_image_one` (494–549) | Parallel image generation, slide `image_path`/metadata persist |
| **Export node** | `application/services/carousel/nodes/export.py` — `run_bilingual_export` (122–167) / `render_language` (59–119) | Render bilingual JPGs + PDFs, set `pdf_path`/`pdf_path_en` |

These four call sites are the **forward port surface** AE-0121 must front (design / images /
export / artifact-build). The finalize artifact-build call is the one that crosses into the
shared CAS, so it is also the AE-0118 coordination point.

### 5.2 Presentation → editorial callback boundary

| Callback | Site | What it writes / signals |
|----------|------|--------------------------|
| **`phase_progress` write** | `nodes/images.py` — `_publish_progress_state` (381–390): sets `phase_progress` on the project (workflow-owned column) + `repo.update_project`, then `publish_workflow_progress` (391–395) to the SSE stream | The presentation image node writing **back** into the workflow-owned `phase_progress` + the editorial SSE progress channel. This is a presentation→editorial **callback** — AE-0121 SHALL model it as a callback/event out of the presentation port (the presentation side must NOT own `phase_progress`; it belongs to editorial per AE-0105 §2.3). |

> Consequence for AE-0118/0121: the image node both **reads** presentation inputs and
> **writes** an editorial-owned column. The port must split these — presentation owns
> `image_path`/slide metadata; the `phase_progress`/SSE emission crosses back to editorial.

### 5.3 Sufficiency for AE-0118/0120/0121

All presentation `carousel_projects` columns (§2), all `CarouselSlideModel` columns (§7),
the shared CAS (§3), the multi-writer set (§4), and the forward+callback boundary (§5.1–5.2)
are mapped with `file:line`. There is **no unmapped presentation surface**: AE-0118 can
scope the presentation ACL + the no-clobber CAS test; AE-0120 can scope the read facade
(§6); AE-0121 can scope the editorial→presentation port (the four forward calls + the one
callback).

---

## 6. `crud.py` project-GET presentation read classification

`api/routes/carousels/crud.py` `get_carousel` (137–150) performs a **presentation read**:
at line 149 it calls `merge_design_tokens_with_disk(project)` and assigns the result to
`project.design_tokens` **on the response object only** — `repo.update_project` is **not**
called, so nothing is persisted (the merge reads on-disk overrides and overlays them onto the
DB `design_tokens` for the response).

**Classification:** presentation-owned read, **served via the presentation facade in
AE-0120.** Rationale: it is a presentation concern (design-token assembly from DB + disk) and
it is the canonical read shape the frontend consumes; centralizing it behind the AE-0120
facade keeps the response bytes byte-identical while removing the route's direct reach into
presentation merge logic. It is **not** deferred-with-rationale — it is an explicit
AE-0120 facade responsibility. (The same `merge_design_tokens_with_disk` is also called on
the *persist* path at `editorial_finalize.py:209`; that write stays on the presentation
write owner — only the **read** at `crud.py:149` moves to the facade.)

---

## 7. `CarouselSlideModel` columns

Source: `models/carousel.py` lines 303–390. Slides are presentation/content artifacts of a
project. Class: **PO** = presentation-owned; **SYS** = DB/system-managed; **⚠ MULTI** = §4.

| Column | Type | Meaning | Writer(s) `file:line` | Class |
|--------|------|---------|------------------------|-------|
| `id` | String(36) PK | Slide UUID | P1 `from_entity` only (model.py:363) | SYS |
| `project_id` | String(36) FK→carousel_projects (CASCADE) | Owning project | P1 create only (model.py:365) | SYS |
| `slide_number` | Integer | Order within carousel | P1 `update_from_entity` (model.py:381) | PO |
| `slide_type` | String(20) | intro/content/summary/closing/cta | P1 (model.py:382) | PO |
| `heading` | Text | Slide heading copy | P1 (model.py:383); **P8** `editorial_distribution_persist.py:110` | PO ⚠ |
| `body` | Text | Slide body copy | P1 (model.py:384); **P8** `editorial_distribution_persist.py:111` | PO ⚠ |
| `html_content` | Text null | Rendered slide HTML | P1 (model.py:385) — no active app writer (entity field; stays NULL in current flow) | PO |
| `image_path` | String(500) null | Hero image path | P1 (model.py:386); **P5** image node `nodes/images.py:285`; **P8** reset `editorial_distribution_persist.py:115` | PO ⚠ |
| `image_prompt` | Text null | Image generation prompt | P1 (model.py:387); **P8** `editorial_distribution_persist.py:112`; **P9** refinement `carousel_refinement.py:165` | PO ⚠ |
| `slide_metadata` (col `metadata`) | JSON NOT NULL (default dict) | Generation metadata (model/provider/SHA/prompts) | P1 (model.py:388); **P5** image node `nodes/images.py:286-293` (`_apply_image_metadata`); **P8** reset `editorial_distribution_persist.py:114` | PO ⚠ |
| `extras` | JSON null | Packed slide extras (features/stats/insight/image_prompt) | P1 (model.py:389); **P8** `editorial_distribution_persist.py:113`; **P9** `carousel_refinement.py:166-168` | PO ⚠ |
| `created_at` | DateTime | Creation timestamp | server_default (model.py:323) | SYS |
| `updated_at` | DateTime | Last-modified timestamp | server `onupdate` + P1 (model.py:390) | SYS |

---

## 8. Out of Phase 5 — distribution & publishing (Phase 6)

The following are explicitly **OUT** of the Phase 5 presentation surface and stay where they
are until Phase 6 (distribution). Confirmed against AE-0105 §2.6 and the model:

| Column | Type | Owning context | Status |
|--------|------|----------------|--------|
| `blog_markdown` | Text null | Distribution | OUT (Phase 6) |
| `blog_translations` | JSON null | Distribution | OUT (Phase 6) |
| `caption` | Text null | Distribution | OUT (Phase 6) |
| `caption_en` | Text null | Distribution | OUT (Phase 6) |
| `linkedin_post_pt` | Text null | Distribution | OUT (Phase 6) |
| `linkedin_post_en` | Text null | Distribution | OUT (Phase 6) |
| `is_public` | Boolean NOT NULL | Identity/ACL (publish path) | OUT — publish/`is_public` path stays (Phase 6 / root ACL) |

Presentation does **not** own blog/caption/linkedin distribution copy, the publish/`is_public`
release path, persona, or workflow state (those are editorial / Phase 6). The publish path
(`crud.py` `publish_carousel`) is untouched by Phase 5.

---

## 9. Summary counts

- **Presentation `carousel_projects` columns mapped:** 23 — 18 presentation-owned (PO),
  5 deferred-within-presentation (DEF, create-only inputs §2.4).
- **`CarouselSlideModel` columns mapped:** 13 — 9 PO, 4 SYS.
- **Distinct writer surfaces:** P1–P10 (10), plus the shared resume CAS owner and the
  read-only `crud.py:149` / `read_project_lock_version` access sites.
- **Multi-writer fields flagged (§4):** 14 — `lock_version`, `artifact_version`,
  `design_tokens`, `pdf_path`, `pdf_path_en`, `primary_color`, `accent_color`,
  `background_color` (project) + slide `image_path`, `image_prompt`, `extras`,
  `slide_metadata`, `heading`, `body`.
- **Shared CAS:** 1 token (`lock_version`) bumped on 2 cross-owner CAS paths (resume +
  activation) — single shared CAS primitive / serialization required (§3.1).
- **Editorial↔presentation boundary:** 4 forward calls (design/images/export/finalize-artifact)
  + 1 callback (`phase_progress`/SSE from images node).
- **Out of Phase 5:** 7 columns (6 distribution + `is_public`/publish) deferred to Phase 6.

---

## 10. References

- ORM model: `backend/src/rag_backend/infrastructure/database/models/carousel.py`
- AE-0105 field map: `docs/architecture/carousel-project-field-ownership.md`
- Phase 5 plan: `docs/plans/phase-5-presentation.md`
- Module conventions: `docs/architecture/module-conventions.md`
- ADR-009 (Domain Modular Monolith): `docs/decisions/0009-adopt-domain-modular-monolith.md`
- Editorial write owner (AE-0107): `backend/src/rag_backend/modules/editorial/infrastructure/carousel_project_write_owner.py`
- Activation CAS: `backend/src/rag_backend/infrastructure/database/carousel_artifact_build_repository.py`
- Resume CAS: `backend/src/rag_backend/application/services/optimistic_lock_service.py`
- Tickets: `.agent/tasks/AE-0115` (this map); blocks AE-0118 / AE-0120 / AE-0121
