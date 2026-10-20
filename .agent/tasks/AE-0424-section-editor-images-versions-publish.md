# AE-0424 — Section editor, per-section/cover images, versions on save, publish button (C)

Status: Done
Tier: T2
Priority: P1
Type: Feature
Area: Cross-cutting
Owner: Claude (worker)
Agent Lane: architect → developer → qa → release
Branch: feat/ae-0424-section-editor
Kanban Card: TBD
Created: 2026-10-18
Updated: 2026-10-19

## Goal

Replace the single markdown textarea with a section editor where the owner edits each section
(heading/body, reorder, add/delete), manages a cover and a per-section image
(generate/regenerate/remove/alt/caption), switches the whole document between **PT and EN**,
rewrites one section in the persona voice, sees the voice score, and gets a version snapshot on
every save plus an unsaved-changes guard, **review actions (submit/approve/reject)**,
**Publish/Unpublish** and **scheduled publish**.

## Problem

The editor is one raw-markdown `<textarea id="blog-post-body">`
(`frontend/src/app/dashboard/blog-posts/[id]/edit/blog-post-edit-fields.tsx:100-115`); no per-section
editing, no image management, no cover (`featured_image_url` has no field), the AI panel is rendered
without a `personaId` (`edit/page.tsx:140-144`, F-11), `version_history` is never appended on save
(`blog_post_versions.py:88`, F-13), there is no unsaved-changes guard (F-12), `ai-suggest` can return
a fenced JSON envelope (F-10), `submitForReview`/`approve`/`publish` are dead code although the
owner wants review + scheduling (F-14), and there is no control to switch the edited content between
PT and EN (the document stores `translations.en` but nothing exposes it). Design: ADR-0025.

## Scope

- Frontend editor:
  - Section cards (edit heading/body, reorder, add/delete) over the `blog.v2` document (AE-0423).
  - Cover slot + per-section image slot: generate (GPT), regenerate with edited prompt, remove, alt,
    caption; visible per-slot retry on failure.
  - **PT/EN language buttons** in the header: switching shows/saves `content.cover` +
    `content.sections` (PT) or `content.translations.en.cover` + `.sections` (EN); the inactive
    language is preserved byte-identically. A missing EN document is read-only with a **"Generate EN
    translation"** action (calls the writer, AE-0425).
  - "Rewrite this section in my voice" → `POST /blog-posts/{id}/sections/{sid}/rewrite`.
  - Voice-score display from `content.quality`.
  - Unsaved-changes guard (route + `beforeunload`).
  - **Review controls:** Submit for review (reviewer), Approve, Reject (reason), Publish, Unpublish,
    and **Schedule** (date/time) — calling the existing `blog_post_workflow` routes; keep `If-Match`
    optimistic locking (AE-0296). `BLOG_ALLOW_SELF_REVIEW` (default **false**) bypasses the submit-time
    `ERR_SELF_REVIEW` guard and stores the author as `reviewer_id` (the existing
    `assert_blog_post_reviewer_or_admin` then accepts approve/reject); when false a distinct
    reviewer is required.
- Backend:
  - `PUT /blog-posts/{id}` appends a `version_history` snapshot (title + content) in the save
    transaction.
  - `POST /blog-posts/{id}/sections/{sid}/rewrite` (PersonaAgent.enforce on one section).
  - Image routes: cover + section generate/regenerate/remove/alt/caption (shared with AE-0425).
  - `ai-suggest` strict JSON (strip fences, unwrap nested envelope, degrade to raw).
- Reconcile `frontend/tests/features/blog_post_editorial.feature` with the new design (drop the
  rich-text-editor promises, keep version history + AI suggest, add section editing + images + the
  PT/EN switch + review/schedule).

## Non-Goals

- The writer, quality gate and full-article generation (AE-0425).
- Owner photo upload (`source: "upload"`).
- Authoring the EN document from scratch: the EN tab edits an existing translation; generating it is
  the writer's job (AE-0425).

## Acceptance Criteria

- [x] AC1: The editor shows one card per section; editing a heading/body and saving persists it, and
      the other sections are preserved.
- [x] AC2: Adding, deleting and reordering sections updates the stored `content.sections`; a
      reordered section keeps its own image and stable id.
- [x] AC3: A section image can be generated, regenerated with an edited prompt, and removed; a
      generated image has a non-empty `alt` (defaulting to the heading) and an optional caption. The
      provider result is **downloaded and persisted** to the blog-images store; only the canonical
      CDN/same-origin URL is stored (a provider URL is never persisted; a persistence failure leaves
      `image = null` and returns the error).
- [x] AC4: The cover can be generated/regenerated/removed; the same persistence rule applies; on
      save `featured_image_url` equals `cover.url` (or `NULL` when the cover is removed).
- [x] AC5: "Rewrite this section in my voice" replaces only that section's `body_md`
      (`PersonaAgent.enforce`); the voice score is shown from `content.quality`.
- [x] AC6: Saving appends a `version_history` entry; the sidebar lists it and restore works (F-13).
- [x] AC7: Leaving the editor with unsaved changes prompts/guards (F-12).
- [x] AC8: `ai-suggest` never returns a fenced ```json envelope as `suggested_text`; a nested
      envelope is unwrapped (F-10).
- [x] AC9: Publish/Unpublish works **through the existing status guards**: Publish is enabled only
      for `approved` (a draft cannot jump to `published`; a 400/status-guard error is shown, not
      swallowed); Publish validates at least one non-empty section (empty → 422, stays `approved`);
      unpublish returns to `draft` (public 404). "Publish now" on a draft auto-submits + self-approves
      when `BLOG_ALLOW_SELF_REVIEW` is enabled; when disabled it is hidden and the editor links to
      the review flow.
- [x] AC10: `blog_post_editorial.feature` is reconciled in place (no dead rich-editor promises).
- [x] AC11: PT/EN buttons switch the whole edited document; editing EN never mutates PT and vice
      versa; saving persists only the active language.
- [x] AC12: An absent EN translation is read-only with a "Generate EN translation" action; after
      generation the EN tab is editable.
- [x] AC13: Submit review → Approve/Reject and Schedule call the existing workflow routes and reflect
      the resulting status; a past schedule timestamp is rejected; `If-Match` guards **every**
      content-mutating call (save, image generate/patch/delete, rewrite, restore); an edit while
      `under_review`/`approved`/scheduled resets to `draft` and clears `scheduled_publish_at`; a
      cancel-schedule action (`DELETE …/schedule`) leaves the post `approved`; with
      `BLOG_ALLOW_SELF_REVIEW` (default **false**) a "Publish now" on a draft auto-submits +
      self-approves, and with it disabled the explicit steps are required.
- [x] AC14: The editor's own copy (buttons, labels, errors) stays localized via next-intl; content
      language (PT/EN) is independent of the UI locale.
- [x] AC15: If a content write fails because the row is still non-v2 (`InvalidBlogDocumentError`),
      the editor shows a blocking "migration pending" banner with the API error and does not attempt
      a client-side v1 parse or persist. The banner clears after the cutover is verified and the post
      is reloaded.

## Gherkin Scenarios

- `frontend/tests/features/blog_editor_ae0424.feature`.
- `backend/tests/features/blog_post_ai_contract_ae0424.feature` (strict JSON, rewrite-section,
  versions on save, **and the full workflow: submit-review, approve, reject, self-review on/off,
  publish guard, schedule/cancel, edit-resets-draft**).
- Scenario list: edit section; add/delete/reorder; generate/regenerate/remove section image; alt
  required; provider image persisted as canonical URL; cover sync/null; rewrite in voice; version
  snapshot on save; unsaved guard; publish only from approved; empty document → 422; unpublish;
  submit review/approve/reject; self-review on/off; schedule a future publish + reject a past one +
  cancel; edit after approval resets to draft; PT/EN switch (edit EN without touching PT; missing EN
  read-only); suggest plain text. **Public PT/EN scenarios live in AE-0423, not here.**

## Delta

### ADDED

- `frontend/src/modules/publishing/blog/components/section-editor/*` (section card, image slot,
  cover slot, **PT/EN language tabs**, **review/schedule bar**), hooks, types, i18n keys.
- Backend: `POST …/sections/{sid}/rewrite`, **the image routes (owned here; AE-0425 reuses the
  service and calls these routes, it adds none)**, version-on-save in the lock path,
  `DELETE …/schedule`, and the `BLOG_ALLOW_SELF_REVIEW` setting (default false).

### MODIFIED

- `blog-post-edit-fields.tsx` → section editor; `edit/page.tsx` (wire persona, publish, guard);
  `use-blog-post-editor.ts`; `use-blog-posts.ts` (publish/unpublish reused); `ai-suggestion-panel.tsx`
  (personaId); `blog_post_ai_service.py` (strict JSON); `optimistic_lock_service` (snapshot);
  `blog_post_editorial.feature`.

### REMOVED

- The single-body textarea as the only editor; the dead `ImageGenModal` unwired state (it is **not**
  reused: the new `section-editor/*` image slots replace it; AE-0428 deletes the old file).

## Affected Areas

- Backend: blog AI contract, version-on-save, rewrite-section, image routes
- Frontend: blog edit page, publishing blog module, i18n
- Database: `version_history` now written (no schema change)
- API: new rewrite/image routes; suggest contract tightened
- Tests: frontend unit + feature; backend feature
- Docs: ADR-0025, this ticket
- Prompts/LLM: persona rewrite uses the existing persona prompt (no new prompt)
- Observability: Langfuse for rewrite calls
- Deployment: normal

## Dependencies

- Blocks: AE-0425 (reuses the image service/routes; adds no routes), AE-0426 (needs editable
  drafts).
- Blocked by: AE-0423 (document shape).
- Related: AE-0296, AE-0411, AE-0416, ADR-0025.

## Implementation Plan

1. Feature specs first.
2. Backend: version-on-save, rewrite-section, strict JSON, image routes + tests.
3. Frontend: section cards, image slots, cover, voice score, guard, publish + tests.
4. Reconcile `blog_post_editorial.feature`.
5. Gates: `bash scripts/ci/gates.sh backend` and `frontend`.

## QA Checklist

- [ ] Security reviewed (markdown XSS, authz on new routes, alt/URL validation)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (empty section, concurrent save 409, image failure retry)
- [ ] Orphan/unfinished code checked (no unwired components)

## Progress Log

### 2026-10-18 16:30

Ticket created from the AE-0422 plan (ADR-0025, wave C).

### 2026-10-19

Implemented backend + frontend (worker, branch `feat/ae-0424-section-editor`, stacked on
`feat/ae-0423-blog-document-model`). Gate evidence in Test Evidence below.

## Files Touched

- Backend: `api/routes/blog_post_images.py`, `blog_post_sections.py`, `blog_post_schedule.py`
  (new); `blog_post.py`, `blog_post_versions.py`, `blog_post_workflow.py`, `blog_post_ai.py`;
  `api/dependencies/blog_content_write.py`, `blog_slot_write.py`, `blog_editor.py` (new);
  `api/schemas/blog_post.py`, `blog_post_editor.py` (new);
  `application/services/blog/{ai_envelope,blog_document_edits,blog_image_service,blog_review_reset,blog_translation_service,blog_version_history}.py`
  (new); `optimistic_lock_service.py`, `blog_post_ai_service.py`;
  `agents/blog_editor_prompts.py` + `agents/prompts/blog/v1/{image_prompt,translate_section}.yaml`;
  `domain/constants/blog_editor.py`; settings `blog_allow_self_review` + `.env.example`.
- Frontend: `modules/publishing/blog/components/section-editor/*` (new),
  `hooks/use-blog-post-editor.ts` (rewritten), `use-blog-editor-actions.ts`,
  `use-blog-review-actions.ts`, `use-blog-editor-data.ts`, `use-unsaved-changes-guard.ts`
  (new), `blog-editor-requests.ts`, `lib/editor-document.ts`, `editor-content.ts`,
  `version-history-sidebar.tsx`, `app/dashboard/blog-posts/[id]/edit/*`,
  `constants/blog-editor.ts`, i18n `dashboard.blogPosts.editor.*` (en + pt).
- Specs reconciled: `blog_post_editorial.feature`, `blog-dashboard-ae0411.feature`,
  `blog-posts-management.feature`.

## Test Evidence

**Review round 1 (2026-10-19), head `e7908227e` rebased onto the latest AE-0423 branch.**

- CI on PR #147: **34/34 checks pass**, including `backend / Test & Coverage`,
  `backend / Mutation (blocking ≥75%)`, `frontend / Test`, Build, Lint, Type Check,
  Integrity, Strict Diff, Architecture, Migrations, Schema drift.
- Local (orchestrator rule 2026-10-19: no local mutation, targeted tests only):
  - backend static gates via `gate-capture.sh backend` — format, lint, lint-diff,
    blanket-ignore, strict-diff, type, imports, arch-ratchet, docstrings, dead-code,
    inline-prompts, redis-factory, autopilot-env, healthcheck-loopback, bandit, pip-audit,
    integrity: 17/17 PASS. The run was stopped before test/mutation (OOM rule); CI ran those.
  - backend targeted pytest (blog editor, review flow, AE-0423 sections, ai service, scheduled
    publish, publishing/presentation safety nets, route snapshot): 280 passed; ruff + mypy clean.
  - frontend: typecheck, eslint, component-types, dead-code, prettier clean; targeted vitest
    (publishing, blog-posts dashboard, public blog): 348 passed.

Earlier full local run (before review round 1): backend 22/22 PASS, frontend 17/17 PASS.

PR: https://github.com/rickwalking/alter-ego/pull/147

## QA Report

Pending.

## Decision Log

- **Review + scheduled publish are in scope (owner revision).** The routes already exist
  (`blog_post_workflow.py`); C exposes them. `BLOG_ALLOW_SELF_REVIEW` (default **false**) bypasses
  only the submit-time `ERR_SELF_REVIEW` guard and records the author as the assigned reviewer,
  keeping the single-author flow usable without weakening the distinct-reviewer rule when disabled.
- **Language buttons switch content, not chrome.** The editor mutates only the active language
  subtree and sends the merged document, so the inactive language is never rewritten. Public `?lang=`
  is the same content-language switch (AE-0423 renders it).
- **Version snapshot in the save transaction.** Appending in `apply_versioned_update` removes the
  chicken-and-egg where restore is the only writer of history.
- **(impl) Mutation routes return the full post.** Image/rewrite/translation/restore answer with
  `BlogPostResponse` (new `lock_version` + status in one reply) instead of `{image}`/`{section}`.
- **(impl) Added routes:** `PATCH …/cover/image`, `POST …/translations/en` (the EN action; the
  AE-0425 writer may replace its internals later), public `GET /blog-images/{post}/{uuid}.jpg`
  (no route served the blog-images store, so a stored path was not a usable URL) and
  `GET /blog-editor/settings` (`allow_self_review` for the editor).
- **(impl) Workflow If-Match:** publish/schedule/cancel check `If-Match` when sent (the editor
  always sends it); they do not bump `lock_version` (status-only writes).
- **(impl) Approval reset:** a `content`/`title`/`excerpt` change on `under_review`/`approved`
  resets to `draft`, clears schedule + review stamps and emits the status event; a published
  post stays published on edit (state diagram).
- **(impl) Persona for "rewrite in my voice":** requested → the post's carousel persona → the
  first persona (single author); none → 422. Output gets the display hardening.
- **(impl) Translation input is not `sanitize_llm_input`-ed** (it strips markdown link
  parentheses); the owner's text is delimited as data in the versioned template.
- **(impl) Editor UX:** alt/caption/remove are draft edits saved with PUT (client + server reject
  a blank alt); generate/regenerate/rewrite/translate save pending edits first, then merge only
  their slot. Workflow buttons are disabled while there are unsaved edits. Save stays in the
  editor (so the new version shows); this reconciles the AE-0296/AE-0411 "returns to the
  listing" lines. Reviewer is an ID input (existing review-assignment pattern). The unsaved
  guard covers tab close, in-app links and the Back button (not the browser back button).
- **(impl) Bugs found and fixed:** `BlogPostResponse.version_history` was `list[str]` (any
  response after a snapshot would 500) and `editor_comments` likewise; reject appended in place
  to a JSON list, so the reason was never persisted.
- **(impl) `BLOG_ALLOW_SELF_REVIEW`** is a Settings field + `.env.example` only; enabling it in
  prod (deploy/compose) is the owner's decision.
- **(review) Post-spend writes re-read the row** under `FOR UPDATE` and apply the slot onto
  the latest document, so concurrent cover + section generation or a Save during the spend
  no longer 409s and orphans a paid image (see the shared contract below).
- **(review) Version entries snapshot the PRE-write state** ("Before save" / "Before restoring
  version n"), so the original (AI) draft is kept; history is capped at
  `BLOG_VERSION_HISTORY_MAX` = 50 (first entry always kept), an unchanged pre-state is not
  re-appended, and `version_history` is no longer in `BlogPostResponse` (`GET /versions`).
- **(review) Status transitions bump `lock_version`** (submit/approve/reject/publish/
  schedule/cancel) and the review reset is decided from the locked row; the editor disables
  the review controls while any slot action runs.
- **(review) One publish guard** (`blog_publish_readiness.assert_ready_to_publish`:
  non-empty document + valid AI-disclosure label) for publish, submit-review, schedule and the
  due-post sweep (a blocked scheduled post stays approved, its schedule is cleared, logged).
- **(review) Rewrite output** is not passed through the input sanitizer (it stripped
  `( ) < >` and truncated at 10k); only a code fence is stripped and the length is checked
  against `BLOG_SECTION_MAX_CHARS`. A body over the 10k LLM input limit is refused (422)
  instead of silently truncated. Note: `PersonaAgent.enforce` still sanitizes its INPUT
  (existing agent behaviour, unchanged here).
- **(review) Images:** real type sniffed (gpt-image-2 returns PNG), unreferenced files pruned
  after every write, per-post budget, draft images author/admin-only.
- **(review) Legacy `POST /generate-image` removed** with `BlogPostAIService.generate_image`,
  `useBlogAi().generateImage` and the dead `ImageGenModal` (AE-0428 has one less file to
  delete).
- **(review) ai-suggest** also finds the envelope in a fenced block or a bare `{…}` after
  leading prose.
- **(review) Editor:** typing during an in-flight save is kept; a save that loses the race to
  our own slot write is retried once on the new lock.
- **(review 2) Prune grace window, cutover stash kept, budget reserved under the lock before
  the spend, transitions re-read their row `FOR UPDATE`** (submit/approve/reject/publish/
  unpublish/schedule/cancel), `docs/architecture/openapi.json` regenerated.
- **(review 2) Gate-script fix `scripts/ci/ruff-strict-changed.sh`:** it resolved
  `origin/main...HEAD` before `changed-backend-files.sh` ran `git fetch origin main --depth=1`,
  which dropped the merge base on this stacked PR once main moved (#143 merged); every per-file
  diff then failed and the gate died under `set -e` with no violation printed. It now lists the
  files first, then resolves the range, and a file without hunks is "nothing to check". Not a
  loosening: `test_ruff_strict_changed.py` reproduces the silent failure and proves a seeded
  PLR0913 on a changed line still fails the gate. Publish/unpublish routes also moved to a
  target dependency (<= 3 args).
- **Image routes are owned by C.** C adds the editor endpoints; D reuses the same service/routes
  for bulk generation and adds no new routes. One route set.


## Shared contract with AE-0425 (image store, image routes, slot writes)

AE-0425 (PR #146) reuses these; changing them is a cross-ticket change.

- **Slot-write path** — `api/dependencies/blog_slot_write.py`:
  1. preflight before any spend: `require_current_version(post, if_match)` (428/409),
     `load_document(post)` (422 non-v2 → editor "migration pending"), slot lookup
     (`edit_or_404`, 404), image budget (`within_budget`, 429);
  2. end the read transaction, spend (provider/LLM);
  3. `apply_slot_edit(db, SlotEdit(post_id, user_id, edit, events, ai_action?,
     metadata_edit?, discard?, change_summary?))`: `SELECT … FOR UPDATE` the row
     (`resource_access.lock_blog_post`), apply `edit` onto the **latest** document by
     section id (only the section must still exist → else 404), store through
     `write_post_content` at the locked `lock_version` (review reset + pre-write version
     snapshot decided from the locked row), commit; on any failure roll back and call
     `discard` (e.g. delete the new file).
- **Image store** — `application/services/blog/blog_image_store.py` (`BlogImageStore`):
  `<carousel_output_dir>/blog-images/<post_id>/<uuid4>.<png|jpg|webp>`; the provider writes
  `<uuid>.part`, `finalize` sniffs the real type and renames. Canonical URL: CDN when
  enabled, else `/api/blog-images/<post_id>/<file>`. `prune(post_id, keep)` +
  `referenced_filenames(content, version_history, featured_image_url, cutover stash)`;
  `api/dependencies/blog_editor.prune_unreferenced_images(post)` runs after every committed
  content write. A file younger than `BLOG_IMAGE_PRUNE_GRACE_SECONDS` (3600) is never
  pruned — it may be an image of a concurrent request (or an AE-0425 batch) still waiting on
  the row lock; the AE-0423 cutover rollback stash
  (`ai_generation_metadata.blog_v2_cutover.featured_image_url`) and the `featured_image_url`
  column count as references.
- **Image service** — `BlogImageService(provider, store, render_prompt)` with
  `agents.blog_editor_prompts.image_prompt` (template `agents/prompts/blog/v1/image_prompt.yaml`);
  `generate(BlogImageRequest(post_id, scene, alt)) -> BlogImage` (model `gpt-image-2`).
- **Image budget** — `api/dependencies/blog_image_budget.reserve_image_budget(db,
  BudgetReservation(post_id, cap, images=1))`: called in the preflight BEFORE the provider
  call; locks the row (`FOR UPDATE` + a per-event-loop asyncio lock), refuses with 429 at
  `BLOG_IMAGE_COST_CAP` (setting `blog_image_cost_cap`, default 30), counts the images in
  `ai_generation_metadata.blog_image_generations` and commits (ending the read
  transaction). The reservation is deliberately kept when the spend or the write fails (the
  provider may have billed it). A batch (AE-0425) reserves per image or `images=n` up front;
  `apply_slot_edit` must NOT count again (no `metadata_edit=count_one_image`).
- **Serving** — `GET /api/blog-images/{post_id}/{uuid}.{ext}`: published → public,
  `max-age=3600, must-revalidate`; otherwise author/admin only with `private, no-store`;
  everyone else gets the uniform 404 (ADR-0013). With the CDN enabled, draft images are
  reachable at unguessable CDN URLs (recorded in ADR-0025).

## Risk & Size

- **Risk:** Medium — large editor surface + version-on-save; mitigated by optimistic locking and focused tests.
- **Size:** L

## Blockers

None.

## Final Summary

**Merged and closed (orchestrator, 2026-10-20).** Merged #147 into the AE-0423 branch (34ff073), shipped to main with #145 (b20a12d, 2026-10-19) after two re-reviews.
