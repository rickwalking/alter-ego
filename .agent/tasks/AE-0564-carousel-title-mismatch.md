# AE-0564 — Publish page heading and sticky header show different carousel titles

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Frontend (create workspace + publish pages)
Owner: Pedro
Agent Lane: developer → qa
Branch: fix/ae-0564-carousel-title-mismatch
Kanban Card: TBD
Created: 2026-10-30

## Goal

Every place in the create flow that names a carousel — the workspace top-bar
breadcrumb, the publish-page top-bar breadcrumb, the publish page `h1` and the
workspace carousel preview — shows the same name: the carousel's display title
(LLM inline markup stripped, trimmed title, topic as fallback), the same rule
the workflow board card has used since the discovery work.

## Problem

Seen by Pedro on carousel `2fe43d2c`: the publish page `h1` and the sticky top
bar showed two different titles. Cause: each surface picked its own label:

- `create/[id]/page.tsx` and `create/[id]/publish/page.tsx` breadcrumbs used
  `project.topic` directly.
- The publish heading (`publish-page-sections.tsx`) used
  `firstNonBlank([project.title, project.topic])`.
- The workspace preview (`create-carousel-preview.tsx`) had a local
  `title?.trim() ? title : topic` helper that did not strip inline markup.

When `title` differs from `topic`, the header and the heading disagree.

## Scope

- One shared helper `carouselDisplayTitle` in `src/lib/` implementing the
  board's display rule (strip `**`/`__`/`<strong>`-style markup, prefer the
  trimmed title, fall back to the stripped topic); the workflow-board adapter
  delegates its card title to the same helper instead of a second copy.
- Wire the helper into: the workspace breadcrumb, the publish breadcrumb, the
  publish page `h1`, and the workspace preview (heading, hero alt text, slide
  alt text).
- Align only surfaces that mean "the carousel's name". The workspace summary
  card's labeled "Tema" row, the brief step (topic as the brief) and the cover
  prompt suggestions (topic as a prompt input) intentionally keep the raw
  topic.

## Non-Goals

- The public slide/blog viewer (`viewer-slides.ts`) and the queue rows keep
  their existing labels.
- No i18n changes (no new user-facing strings).
- No backend changes.

## Acceptance Criteria

- [ ] AC1 Given a carousel with a non-blank title, When the owner opens the
  publish page, Then the sticky-header breadcrumb and the page `h1` both show
  the title.
- [ ] AC2 Given a carousel with a blank (null, empty or whitespace) title,
  When the owner opens the publish page, Then the sticky-header breadcrumb and
  the page `h1` both show the topic.
- [ ] AC3 Given the create workspace of the same carousels, Then its top-bar
  breadcrumb shows the same display title (title when set, topic otherwise).
- [ ] AC4 Given a title or topic with LLM inline markup (`**bold**`,
  `<strong>`), Then every surface strips the markup (the same rule the board
  card applies).
- [ ] AC5 Given the workspace preview, Then its heading uses the same display
  title as the breadcrumbs and the publish heading.

## Gherkin Scenarios

- `frontend/tests/features/carousel-title-consistency-ae0564.feature`

## References

- Files: `src/lib/carousel-display-title.ts` (new helper),
  `src/modules/editorial-operations/board/workflow/adapters/workflow-adapter.ts`
  (delegates to the helper),
  `src/app/dashboard/create/[id]/page.tsx`,
  `src/app/dashboard/create/[id]/publish/page.tsx`,
  `src/app/dashboard/create/[id]/publish/publish-page-sections.tsx`,
  `src/app/dashboard/create/workspace/create-carousel-preview.tsx`.

## Dev Notes

- Decision attributed to Pedro (2026-10-30): a single display-name rule
  reused everywhere, matching the workflow board card rule instead of adding a
  second one.
- No comments in source (JSDoc only); no ticket ids in repo text.
- The board adapter's card-description logic (`boardDescription`) is
  unchanged apart from importing the shared markup stripper.
