# AE-0428 — Delete blog v1 dead code and drop `blog_image_map` (F)

Status: Intake
Tier: T2
Priority: P2
Type: Refactor
Area: Cross-cutting
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-10-18
Updated: 2026-10-18

## Goal

Remove the blog-v1 machinery that ADR-0025 replaces instead of leaving it behind a flag: drop the
blog-only `blog_image_map` field end-to-end and delete the dead/unreferenced frontend and backend
files, their tests/fixtures, and their Knip baseline entries. Add a no-regression guard so the old
symbols cannot reappear.

## Problem

After AE-0422..AE-0426 the v2 document owns structure, voice and images. The v1 files remain:
`blog_image_map` is still persisted in the carousel design payload and typed in the frontend even
though nothing reads it; several components/hooks are already dead (barrel-only or test-only) and
inflate the Knip baseline; and the unreferenced `carousel/nodes/content/` package remains as a
misleading alternative to the new writer. Keeping this invites a future change to re-introduce the
F-01/F-07 class (positional slide images) and makes dead-code audits noisy.

Evidence: `docs/architecture/blog-post-document-model.md` §8 (inventory) and the AE-0422 exploration
inventory (grep/knip).

## Scope

- **`blog_image_map` end-to-end:** remove from
  `domain/models/carousel.py:146`, `nodes/content/core.py:146-159`,
  `carousel_template/design.py:77`, `api/schemas/carousel.py:247`,
  `api/routes/carousels/media.py:262`, `api/routes/carousels/preview.py:218`,
  `frontend/src/schemas/carousel.ts:31`, and `blog-post-content.tsx:215`, plus tests/fixtures.
- **Frontend dead files:** `image-gen-modal.tsx`, `seo-preview.tsx`,
  `accessibility-checker.tsx`, `keyboard-shortcuts-help.tsx`, the `blog-post-filters.tsx`
  *component* (keep the live `BlogPostFilters` type), `hooks/use-accessibility-check.ts`,
  `hooks/use-seo-analysis.ts`, `hooks/use-editor-shortcuts.ts`,
  `hooks/use-carousel-blog.ts` (v1 `useCarouselProject` family — keep the live editorial
  `useCarouselProject`), `adapters/blog-post-adapter.ts`, the orphan `hooks/index.ts` barrel,
  `constants/editor-shortcuts.ts`, `constants/seo.ts`, `blog-post-admin-panel.tsx`,
  `server-fetch.ts::fetchBlogWithDesignCombined`, the v1 blog schema types in
  `schemas/carousel.ts` (`CarouselBlogI18nResponse`, `CarouselBlogWithDesignResponse`,
  `CarouselBlogImageMapEntry`), `constants/blog.ts::CAROUSEL_SLIDE_WIDTH/HEIGHT`, and the v1 query
  helpers in `modules/carousel-presentation/queries.ts` (`carouselBlogOptions`,
  `carouselBlogWithDesignOptions`, `carouselDesignOptions`, `carouselSlidesOptions`,
  `carouselProjectsOptions` — keep the live `carouselProjectOptions`). Remove their barrel exports
  and tests. `public-blog.ts` / `public-blog-cards.ts` / `blog-post-content.tsx` are **rewritten**
  for v2, not deleted.
- **Backend dead code:** the unreferenced `carousel/nodes/content/` package (only a unit test
  imports it).
- **Temporary cutover read fail-safe:** remove the AE-0423 adapter that turns legacy markdown into a
  read-only v2 document plus its `blog_v2_non_migrated_rows` metric and tests. Only do this after
  prod `blog_v1_to_v2 --verify` reports zero non-v2 rows (including translations).
- Remove the matching `frontend/scripts/dead-code-baseline.json` entries.

## Non-Goals

- Deleting the live public blog feed/cards or the editorial carousel hooks with the same names.
- **`carousel/blog_composition.py` and `carousel/editorial_distribution_blog.py`:** these are NOT
  dead — `editorial_distribution_pack.py` uses them to build the carousel's PT/EN distribution blog
  text, and `phase_artifact_runner.py` imports `research_summary_from_findings` from
  `blog_composition.py`. Deleting them would change carousel distribution, which ADR-0025 freezes.
- **`carousel_projects.blog_markdown` / `blog_translations` columns:** still written and read by the
  editorial distribution pack (`editorial_distribution_pack.py:166,186`), so they are not read-dead.
  Do not drop them.
- **`carousel_blog_dual_write.py`:** `sync_carousel_blog_post` is removed in AE-0422 (it clobbers v2
  and re-publishes posts); the delete-time `detach_carousel_blog_posts` is retained. Do not touch
  this module here.
- Any behavior change to v2 (this is a deletion ticket).

## Acceptance Criteria

- [ ] AC1: `blog_image_map` appears nowhere in **code** under `backend/src/` or `frontend/src/`
      (`*.py`, `*.ts`, `*.tsx`; grep test), and
  the carousel design response no longer contains the key.
- [ ] AC2: Every file listed in Scope §"Frontend dead files" is deleted; no barrel re-export
  references it; `npm run typecheck`, `npm run lint` and the frontend tests pass.
- [ ] AC3: The `carousel/nodes/content/` package is deleted; no `src/` or test import remains (the
  content-synthesis unit test is removed or rewritten against the live path).
- [ ] AC4: The live carousel distribution helpers (`blog_composition.py`,
  `editorial_distribution_blog.py`) and the `carousel_projects.blog_markdown`/`blog_translations`
  columns are still present and green; a test proves the distribution pack still builds PT/EN blog
  text (no over-deletion).
- [ ] AC5: `frontend/scripts/dead-code-baseline.json` no longer lists the removed symbols and Knip
  passes with a **stricter** baseline (not a looser one).
- [ ] AC6: A seeded-violation test proves the guard fires: writing a `blog_image_map` reference (or a
  deleted v1 symbol) into a temporary `*.py`/`*.ts`/`*.tsx` file under a scanned root makes the
  static test fail with a
  non-zero exit naming the file (AE-0180).
- [ ] AC7: Live same-name symbols are preserved (`BlogPostFilters` type, editorial
  `useCarouselProject`, `mapBlogPostToDashboard`); typecheck proves it.
- [ ] AC8: The AE-0423 read fail-safe is deleted (no legacy-markdown → v2 adapter, no
  `blog_v2_non_migrated_rows` metric) and a regression test proves a non-v2 read now fails closed
  with the standard error/404 rather than adapting. The removal is gated on prod `--verify` zero;
  record that evidence in Test Evidence.

## Gherkin Scenarios

```gherkin
Feature: Blog v1 dead code is gone

  Scenario: Carousel design payload has no blog image map
    Given a carousel with design tokens
    When the client fetches /api/carousels/{id}/design
    Then the response images object has no blog_image_map key

  Scenario: No v1 symbol survives in the code trees
    Given the cleanup is complete
    When the static guard scans backend/src and frontend/src (code files only)
    Then it finds no blog_image_map reference
    And it finds no v1 markdown-builder symbol
    And the carousel content prompt YAML may still mention blog_image_map (excluded, see Decision Log)

  Scenario: The guard fires on a seeded violation
    Given a temporary source file that reintroduces blog_image_map
    When the static guard runs
    Then it exits non-zero and names the offending file
```

## Delta

### ADDED

- A static no-regression guard (grep/script test) for `blog_image_map` and the v1 builder symbols.

### MODIFIED

- Carousel design schema/payload and its fixtures (key removed).
- `frontend/scripts/dead-code-baseline.json` (entries removed).

### REMOVED

- `blog_image_map` field/type/read path.
- The dead frontend components/hooks/constants and their barrel exports/tests.
- The unreferenced `carousel/nodes/content/` package.

## Affected Areas

- Backend: carousel domain/schema/design and the unreferenced `nodes/content/` package
- Frontend: publishing/blog dead components/hooks/adapters/constants, carousel schema
- Database: none in this ticket (column drop is a follow-up migration)
- API: carousel design response loses `blog_image_map`
- Tests: delete dead tests/fixtures; add the static guard + seeded-violation test
- Docs: ADR-0025 §Cleanup, architecture §8
- Prompts/LLM: none
- Observability: none
- Deployment: normal

## Dependencies

- Blocks: none.
- Blocked by: AE-0422 (blog stops reading `blog_image_map`), AE-0423 (v2 read path + dual-write
  removal) **and a prod `--verify` zero-non-v2 report**, AE-0424 (new image controls replace
  `ImageGenModal`); may run before/after AE-0426.
- Related: AE-0424, AE-0426, ADR-0025, ADR-0009, ADR-0018 (dead-code baseline).

## Implementation Plan

1. Confirm no production caller remains for each file (grep by path and symbol).
2. Remove `blog_image_map` from the backend model/schema/design/content-synthesis and update
   fixtures/tests.
3. Delete the dead frontend files and their barrel exports; preserve the live same-name symbols.
4. Delete the frontend schema key and the v1 renderer reference.
5. Delete `carousel/nodes/content/`.
6. Delete the AE-0423 cutover read fail-safe + metric, after confirming prod `--verify` is zero.
7. Trim the Knip baseline; run `npm run lint`, `npm run typecheck`, `npm test`, and
   `bash scripts/ci/gates.sh frontend` + `backend`.
8. Add the static guard and its seeded-violation test.
9. Confirm `grep -r --include='*.py' --include='*.ts' --include='*.tsx' blog_image_map
   backend/src frontend/src` is empty (YAML prompts are excluded) and the distribution pack tests
   still pass.

## QA Checklist

- [ ] Security reviewed (no authz/URL behavior changed)
- [ ] Code quality reviewed (no over-deletion of same-name live symbols)
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (Knip baseline still passes; guard fires on a seeded violation)
- [ ] Orphan/unfinished code checked (no dangling imports, no empty barrels)

## Progress Log

### 2026-10-18 17:05

Ticket created after the owner revision: drop `blog_image_map` and delete the blog-v1 dead code.
Updated: the carousel distribution helpers and the `blog_markdown` columns are live and excluded;
the dual-write upsert moved to AE-0422 (it would clobber v2); the delete-time detach stays.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- **Delete, don't flag.** A v1 fallback would keep the positional-image failure class alive; ADR-0025
  drops v1 entirely, so the code goes with it.
- **Same-name symbols need a map.** `BlogPostFilters` (type vs component), `useCarouselProject`
  (publishing v1 vs editorial live), and `mapBlogPostToDashboard` are easy to over-delete; the ticket
  names the survivors.
- **Prompts are frozen, not rewritten.** `carousel/v1/content_prompt.yaml:45` and
  `carousel/v2/content_prompt.yaml:45` still mention `blog_image_map`; the parser ignores the key and
  the frozen pipeline stays untouched (no v3 prompt in this ticket). The guard therefore scans code
  extensions only, and a scenario documents the exclusion.
- **Own feature file.** `backend/tests/features/blog_cleanup_ae0428.feature` holds the design-payload
  and static-guard scenarios moved out of AE-0423.
- **Do not over-delete the distribution path.** `blog_composition.py` /
  `editorial_distribution_blog.py` and the `carousel_projects.blog_markdown` columns are live for the
  carousel's editorial distribution pack; only genuinely unused code is in scope.
- **Guard must fire.** Per AE-0180, a green tree is not evidence; the seeded-violation test proves
  the grep guard catches a reintroduced symbol.

## Risk & Size

- **Risk:** Medium — wide deletion surface with same-name live symbols; mitigated by grep/knip
  checks and typecheck.
- **Size:** M

## Blockers

None.

## Final Summary

Pending.
