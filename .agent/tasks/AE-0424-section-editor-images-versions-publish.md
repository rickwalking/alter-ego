# AE-0424 — Section editor, per-section/cover images, versions on save, publish button (C)

Status: Dev Complete
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

Full local runs via `bash scripts/ci/gate-capture.sh <scope>` (`GATES_BASE_REF=origin/main`,
backend with a throwaway Postgres `DATABASE_URL`), 2026-10-19:

- backend — 22/22 PASS (incl. test, diff-cover, migrations, schema-drift, mutation):
  `GATES_JSON: {"pass":22,"fail":0,"skip":0,"results":[{"gate":"backend:format","status":"PASS"},{"gate":"backend:lint","status":"PASS"},{"gate":"backend:lint-diff","status":"PASS"},{"gate":"backend:blanket-ignore","status":"PASS"},{"gate":"backend:strict-diff","status":"PASS"},{"gate":"backend:type","status":"PASS"},{"gate":"backend:imports","status":"PASS"},{"gate":"backend:arch-ratchet","status":"PASS"},{"gate":"backend:docstrings","status":"PASS"},{"gate":"backend:dead-code","status":"PASS"},{"gate":"backend:inline-prompts","status":"PASS"},{"gate":"backend:redis-factory","status":"PASS"},{"gate":"backend:autopilot-env","status":"PASS"},{"gate":"backend:healthcheck-loopback","status":"PASS"},{"gate":"backend:bandit","status":"PASS"},{"gate":"backend:pip-audit","status":"PASS"},{"gate":"backend:integrity","status":"PASS"},{"gate":"backend:test","status":"PASS"},{"gate":"backend:diff-cover","status":"PASS"},{"gate":"backend:migrations","status":"PASS"},{"gate":"backend:schema-drift","status":"PASS"},{"gate":"backend:mutation","status":"PASS"}]}`
- frontend — 17/17 PASS:
  `GATES_JSON: {"pass":17,"fail":0,"skip":0,"results":[{"gate":"frontend:lint","status":"PASS"},{"gate":"frontend:lint-changed","status":"PASS"},{"gate":"frontend:component-types","status":"PASS"},{"gate":"frontend:duplication","status":"PASS"},{"gate":"frontend:dead-code","status":"PASS"},{"gate":"frontend:typecheck","status":"PASS"},{"gate":"frontend:build","status":"PASS"},{"gate":"frontend:legacy-guard","status":"PASS"},{"gate":"frontend:legacy-inventory","status":"PASS"},{"gate":"frontend:format","status":"PASS"},{"gate":"frontend:security","status":"PASS"},{"gate":"frontend:integrity","status":"PASS"},{"gate":"frontend:test","status":"PASS"},{"gate":"frontend:schema-drift","status":"PASS"},{"gate":"frontend:duplication-tests","status":"PASS"},{"gate":"frontend:dead-files","status":"PASS"},{"gate":"frontend:mutation","status":"PASS"}]}`

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
- **Image routes are owned by C.** C adds the editor endpoints; D reuses the same service/routes
  for bulk generation and adds no new routes. One route set.

## Risk & Size

- **Risk:** Medium — large editor surface + version-on-save; mitigated by optimistic locking and focused tests.
- **Size:** L

## Blockers

None.

## Final Summary

Pending.
