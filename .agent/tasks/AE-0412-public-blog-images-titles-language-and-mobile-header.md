# AE-0412 — Public blog: images, titles, language and mobile header

Status: In Development
Tier: T1
Priority: P1
Type: Bug
Area: Cross-cutting
Owner: Claude (owner-requested QA fix)
Agent Lane: developer → qa → release
Branch: fix/ae-0412-public-blog
Kanban Card: TBD
Created: 2026-10-17
Updated: 2026-10-17

## Goal

Anonymous visitors of `/`, `/blog` and `/blog/{id}` see working images (or no image, never a
broken one), clean titles, content in their language with per-post metadata, and a header that
fits a 390px screen.

## Problem

QA 2026-10-16 (`~/alter-ego-qa/2026-10-16-ui/REPORT.md`):

- **B08** — `/blog` cards and post heroes request `/api/carousels/{id}/preview/images/slide_1.jpg`
  (owner-only, 401 for visitors). The homepage maps that to `/images/slide_1.jpg`, which 404s for
  carousels whose images only exist as rendered slides (`<output>/pt|en[/hd]/`).
  Root causes: (1) `editorial_finalize` persists the draft-time merge, so the stored
  `design_tokens.images.hero` is a preview URL, and `merge_design_tokens_with_disk` lets that stored
  value win once the carousel is public; (2) the list page used `tokens.images.hero` raw; (3) the
  public `/images/{filename}` route only looks in `<output>/images/`, while the preview route also
  falls back to `<output>/{lang}/hd` and `<output>/{lang}`; (4) `toPublicCarouselImageUrl` dropped
  `?lang=`.
- **B21** — titles carry `<strong>` (shown raw in cards, H1 and body); `title_en` "slide"
  (placeholder) used as a title; a long niche sentence rendered as the category chip; subtitles
  repeating the title.
- **B22** — "Swipe →" always English (public `/design` hardcodes EN); dates in server-default
  M/D/YYYY; every post page had the generic `<title>`.
- **B23** — the public header has fixed 28px gaps and the brand text; at 390px it overflows (413px)
  and cuts the PT button.

## Scope

1. Backend: `merge_design_tokens_with_disk` maps owner-only preview image URLs to
   `/api/carousels/{id}/images/{file}?lang={lang}` for public carousels.
2. Backend: public `GET /{id}/images/{filename}` accepts `?lang=` (default pt) and falls back from
   the raw image to the rendered slide of that language (standard, then HD) — preview parity.
3. Frontend: `toPublicCarouselImageUrl` keeps `?lang=`; the list page, post page and homepage
   cards go through it; `PublicCoverImage` removes the image frame on load error.
4. Frontend: `public-blog-text` helpers — strip emphasis markup in titles, convert emphasis HTML
   to markdown in the body, skip placeholder titles, short category chip only, locale dates.
5. Frontend: post page `generateMetadata` (title, description, Open Graph), translated swipe hint
   (`blog.swipeHint`), "untitled" fallback (`blog.untitledPost`).
6. Frontend: responsive public header (brand text hidden < sm, smaller gaps/padding).

## Non-Goals

- The English lead paragraph in PT blog bodies: it is the English `research_summary` that
  `blog_composition.py` prepends to both languages (generation pipeline, QA B14). Not fixed here.
- Translating free-text niches ("AI MODELS"): user-entered, single language.
- No production data fix (stored preview URLs are corrected on read).

## Acceptance Criteria

- [x] AC1: No public page requests a `/preview/images/` URL; the hero keeps its language.
- [x] AC2: Public `/images/slide_1.jpg?lang=en` serves `en/slide_1.jpg` (or `en/hd/`) when no raw
  image exists; the raw image still wins; a missing file is 404; a draft carousel is not served.
- [x] AC3: An image that fails to load removes its frame (cards, hero, homepage) — no broken image.
- [x] AC4: Titles never show `<strong>`/`**`; the body renders emphasis as `<strong>`.
- [x] AC5: A placeholder title ("slide", "slide_3", "intro", …) falls back to the next real title
  (other language, topic, public post title), else the localized "untitled" label.
- [x] AC6: A niche longer than 32 chars or 4 words is not shown as a chip; a subtitle equal to the
  title is not shown.
- [x] AC7: Dates are `14/10/2026` (pt) / `Oct 14, 2026` (en); an invalid date prints nothing.
- [x] AC8: The post header hint is "Deslize →" in pt and "Swipe →" in en.
- [x] AC9: Each post page has `<title>` "{post title} · Pedro Marins · Blog" and a description.
- [x] AC10: At 390px `/blog` and a post page have no horizontal overflow and both language
  buttons are visible.

## Gherkin Scenarios

- `frontend/tests/features/public-blog-polish-ae0412.feature`
- `backend/tests/features/public_carousel_images_ae0412.feature`

## Affected Areas

- Backend: `api/routes/carousels/media.py`, `application/services/carousel/design_token_utils.py`
- Frontend: `app/(public)/blog/**`, `app/(public)/(marketing)/marketing-{helpers,post-cards}`,
  `lib/{carousel-media-url,public-blog,public-blog-cards,public-blog-text}.ts`,
  `components/layout/public-header.tsx`, `modules/publishing/blog/components/{listing,public-post}`
- Database: none
- API: `GET /api/carousels/{id}/images/{filename}` gains optional `lang` query (additive)
- Tests: see Test Evidence
- Docs: this ticket
- Prompts/LLM: none

## Dependencies

- Related: AE-0297 (public blog API), B14 (research summary in blog body)

## QA Checklist

- [x] Security reviewed (path traversal still confined; draft carousels still private)
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-17

Ticket created; root causes re-verified against prod read-only (logged-out GETs) and current
main; fixes, tests and a 390px browser check against prod data done.

## Test Evidence

- Backend: `tests/unit/api/test_public_carousel_image_ae0412.py` (11 tests).
- Frontend: `lib/public-blog-text.test.ts`, `lib/public-blog-cards.test.ts`,
  `lib/public-blog.test.ts` (+5), `lib/carousel-media-url.test.ts`,
  `app/(public)/blog/[id]/page.test.ts`, `listing/neon-blog-post-card.test.tsx`,
  `public-post/public-cover-image.test.tsx`, hero/header tests updated.
- Browser (dev server against prod API, logged out, 390px): `/blog` scrollWidth 382 = clientWidth,
  no 401, titles clean, PT post shows "Deslize →", `<title>` per post, `99886e71?lang=en` titled
  "Gemini 4 Argon chegou…" instead of "slide". The two carousels whose public image 404s on the
  current prod backend render without an image (fixed by the backend change once deployed).

## Blockers

None.
