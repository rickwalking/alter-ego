# AE-0416 — QA follow-ups: PT blog body, publish viewer, board, locale, paging

Status: In Development
Tier: T2
Priority: P1
Type: Bug
Area: Cross-cutting
Owner: Claude (owner-requested QA follow-ups)
Agent Lane: developer → qa → release
Branch: fix/ae-0416-qa-followups
Kanban Card: TBD
Created: 2026-10-17
Updated: 2026-10-17

## Goal

Fix the bugs that the 2026-10-16 QA wave (PRs #128–#132, AE-0411..AE-0415) found and left
unfixed: a PT blog body that opens in English, a publish viewer with the wrong slide count and a
PT caption on the EN tab, rejected cards in the "Brief" column, a cookie-only locale, a blog
dashboard capped at 100 posts, and a dead rich-text editor.

## Problem

Each item was re-checked against `github/main` (57b6bd9c) before fixing:

1. **PT blog body starts in English.** `blog_composition.build_blog_markdown_from_long_form_notes`
   (PT) and `…_en_…` (EN) both put `research_summary` right after the title. The summary comes from
   `PROMPT_SOURCE_SYNTHESIS`, an English prompt with no target language, so the PT post opened
   with an English paragraph.
2. **Publish viewer "1 / 6" for an 8-slide project; EN tab shows the PT caption.** The viewer
   counted `design_tokens.images.rendered_slides_*` (merged with whatever is on disk), which can
   list an older render. `GET /api/carousels/{id}` returns `slides: []` (the entity carries no
   slide rows), so the frontend never had the real list from that endpoint. The Instagram caption
   is a single PT field: `caption_en` has no producer (AE-0206 deletes it), and the EN viewer tab
   showed the PT caption with no hint. The slide alt text always used the PT title.
3. **Rejected cards in the "Brief" column.** `PublishingReadAcl.project_board` grouped by
   `current_phase` only; rejected projects (the phase-5 migration maps failed carousels to
   `brief`/`rejected`; timeouts reject at the current phase) sat in their phase column.
4. **Locale ignores `Accept-Language`.** `i18n/request.ts` read only the `locale` cookie. The same
   cookie-only snippet was copied in `app/layout.tsx`, `public-header.tsx`, `/blog`, `/blog/[id]`
   and the marketing home page.
5. **Blog dashboard loads at most 100 posts.** The page made one `limit=100` request and filtered
   status/search on the client, so posts after 100 could not be reached or found.
6. **`RichTextEditor` is dead.** After AE-0411 nothing imports it; it was only re-exported from
   `@/modules/publishing`, and it was the only user of the three `@tiptap/*` packages.
7. **Hardcoded English in these areas:** slide alt text `"… – slide N"`, the dashboard post date
   (always `en-US`).

## Scope

- Backend: PT body without the research intro; EN keeps it; Rejected board column.
- Frontend: viewer counts the workflow slides, placeholder for unrendered slides, EN alt text,
  PT-only caption notice; one locale resolver (cookie → Accept-Language → default); server-side
  paging, status and search on the blog dashboard; remove `RichTextEditor` + TipTap; i18n.

## Non-Goals

- Generating an EN Instagram caption (no producer exists; AE-0206 removes `caption_en`).
- Translating the research summary to PT (an extra LLM call per carousel for an intro).
- Rewriting stored `blog_markdown` / `blog_translations` of existing projects (no data change;
  the fix applies to the next distribution build).
- The research filter / sanitizer / content-gate files (PR #132, AE-0413).
- Hardcoded strings outside these areas (`chat-adapter.ts` "Just now", `rubric-adapter.ts`).

## Acceptance Criteria

- [x] AC1: The PT blog markdown is `# title` then the first section; it never contains the
      research summary. The EN markdown keeps the summary as the first paragraph.
- [x] AC2: With 8 workflow slides and 6 token slides the viewer shows "1 / 8" and 8 images
      (`slide_N.jpg?lang=…`); without workflow slides it falls back to the tokens.
- [x] AC3: A slide image that fails to load shows "Slide not rendered yet".
- [x] AC4: On the EN viewer tab the images ask for `lang=en`, the alt text uses `title_en`, and
      the Instagram tab shows a note that the caption is Portuguese only; the caption field is
      labelled "Instagram caption (PT)".
- [x] AC5: The workflow board has a last column `rejected` with every `phase_status=rejected`
      project; the cards keep their real phase, shown as the badge; the column is localized.
- [x] AC6: The request locale is the valid `locale` cookie, else the best supported
      Accept-Language match (quality-ordered, `pt-BR` → `pt`, `q=0` refused), else `en`; every
      server reader uses the same resolver.
- [x] AC7: The blog dashboard requests 24 posts per page with `offset`; status and search go to
      the API and reset to page 1; a pager shows "Page n of m" and hides for one page.
- [x] AC8: `RichTextEditor`, its props type and the `@tiptap/*` dependencies are removed.
- [x] AC9: New strings exist in en and pt; dashboard dates follow the dashboard language.

## Gherkin Scenarios

- `backend/tests/features/qa_followups_ae0416.feature`
- `frontend/tests/features/qa-followups-ae0416.feature`

## Delta

### ADDED

- Backend: `BOARD_COLUMN_REJECTED`, `BOARD_COLUMNS` (publishing constants).
- Frontend: `i18n/locale.ts` (`resolveLocale`, `matchAcceptLanguage`), `i18n/request-locale.ts`
  (`getRequestLocale`), `distribution/lib/viewer-slides.ts`, `blog-posts-paging.ts`,
  `use-blog-posts-paging.ts`, `blog-posts-pager.tsx`, i18n keys (`publish.carouselViewer.slideAlt`,
  `slideNotRendered`, `publish.instagram.captionPtOnly`, `workflow.board.rejectedColumn`,
  `dashboard.blogPosts.pager.*`).

### MODIFIED

- `blog_composition.py` (PT builder drops the research intro), `editorial_distribution_pack.py`
  (research only to the EN context), `publishing_read_acl.project_board` (Rejected column),
  golden snapshot `tests/snapshots/publishing/workflow_board.json` (+ empty `rejected` column).
- `PublishPanel` (`slideNumbers` prop, EN note, EN alt), `HorizontalCarouselViewer` (placeholder,
  i18n alt), publish page (passes the workflow slide numbers), `localize-board.ts` + board page,
  `i18n/request.ts` and the five server readers, `LanguageSwitcher` (shared cookie constant),
  blog dashboard page, `formatBlogPostDate(date, locale)`.

### REMOVED

- `RichTextEditor` component + `RichTextEditorProps`; `@tiptap/pm`, `@tiptap/react`,
  `@tiptap/starter-kit`.
- `filterBlogPosts` + the editorial-operations `BlogPostFilters` type (client-side filtering
  replaced by the API filters) and their two unit tests.

## Affected Areas

- Backend: carousel blog composition, publishing read ACL (workflow board)
- Frontend: i18n, publish page / distribution module, workflow board, blog dashboard
- Database: none (no migration)
- API: `GET /api/workflow-board` gains a trailing `rejected` column
- Tests: backend unit (+ golden snapshot), frontend vitest
- Docs: this ticket
- Prompts/LLM: none
- Observability: none
- Deployment: none (dependency removal only)

## Dependencies

- Blocks: none
- Blocked by: none
- Related: AE-0411, AE-0412, AE-0413, AE-0414, AE-0415, AE-0347, AE-0206

## Implementation Plan

1. Gherkin features (backend + frontend).
2. Backend: blog composition, board column, tests, snapshot.
3. Frontend: locale resolver, board column, publish viewer, paging, dead code, i18n.
4. Gates: `scripts/ci/gates.sh backend` / `frontend`; CI for the DB gates and mutation.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-17 18:00

Ticket created from the AE-0416 brief; each item re-verified on `github/main` 57b6bd9c.
Implementation, tests and gates in branch `fix/ae-0416-qa-followups`.

## Files Touched

See the PR diff.

## Test Evidence

See the PR body (gate runs).

## QA Report

Pending.

## Decision Log

- **Item 1: omit, not translate.** The research summary has no language contract (English
  prompt, no target language), and translating it would add an LLM call per build for a single
  intro paragraph. The PT body now starts with the first section; the EN body keeps the intro.
  Stored bodies of existing projects are not rewritten (no data change, per the brief).
  Since AE-0413 (#132) research hits may be PT or EN, so a summary of PT sources can be
  Portuguese; the EN body keeps the intro as before (pre-existing, out of scope here).
- **Item 2: the "real slide list" is the workflow state.** `GET /api/carousels/{id}` returns no
  slide rows, but the publish page already loads the workflow state; `resolveLocalizedSlides`
  (the list the slide text editor uses) gives the slide numbers. The viewer builds
  `slide_N.jpg` preview URLs from them (the preview route resolves per language, HD first), and
  falls back to the design tokens when no list exists. A slide whose image 404s shows a
  placeholder instead of a broken image, so the count stays honest.
- **Item 2: no EN Instagram caption.** The account publishes one PT caption; `caption_en` has no
  producer and AE-0206 removes it. Generating one would be a new backend feature. Instead the
  caption field is labelled "(PT)" and the EN tab says the caption is Portuguese only (the EN
  copy lives in the LinkedIn EN post and the EN PDF). The slide alt text follows the tab.
- **Item 3: own column, not a filter.** A trailing `rejected` column (value = the existing
  `PHASE_STATUS_REJECTED`) keeps the board one request and needs no new UI control. Cards keep
  their real `current_phase`; the frontend shows it as the badge ("Content") because the column
  already says "Rejected". `BOARD_PHASES` (the phase list) is unchanged.
- **Item 4: one resolver.** `resolveLocale` is pure (unit-tested); `getRequestLocale` reads the
  cookie and header and replaces the six copies, so the `<html lang>`, the public header and the
  blog pages always agree with next-intl's messages.
- **Item 5: pages, server-side filters.** "Load more" with client filtering would still miss
  unloaded posts, so status and search now go to the API (`status`, `search` already existed)
  and reset to page 1; 24 posts per page; search waits 300 ms after typing. The API search
  matches title and slug (the old client filter matched title and excerpt). The status filter
  stays mounted while a page loads.
- **Item 6: removed.** Truly dead (no importer, no test, no story); the TipTap packages had no
  other user. `filterBlogPosts` became dead with item 5 and is removed too.

## Blockers

None.

## Final Summary

Pending.
