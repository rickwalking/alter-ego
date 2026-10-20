# AE-0428 — Delete blog v1 dead code and drop `blog_image_map` (F)

Status: Dev Complete
Tier: T2
Priority: P2
Type: Refactor
Area: Cross-cutting
Owner: Developer (worker)
Agent Lane: architect → developer → qa → release
Branch: feat/ae-0428-delete-blog-v1-dead-code
Kanban Card: TBD
Created: 2026-10-18
Updated: 2026-10-19

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

- [x] AC1: `blog_image_map` appears nowhere in **code** under `backend/src/` or `frontend/src/`
      (`*.py`, `*.ts`, `*.tsx`; grep test), and
  the carousel design response no longer contains the key.
- [x] AC2: Every file listed in Scope §"Frontend dead files" is deleted; no barrel re-export
  references it; `npm run typecheck`, `npm run lint` and the frontend tests pass.
- [x] AC3: The `carousel/nodes/content/` package is deleted; no `src/` or test import remains (the
  content-synthesis unit test is removed or rewritten against the live path).
- [x] AC4: The live carousel distribution helpers (`blog_composition.py`,
  `editorial_distribution_blog.py`) and the `carousel_projects.blog_markdown`/`blog_translations`
  columns are still present and green; a test proves the distribution pack still builds PT/EN blog
  text (no over-deletion).
- [x] AC5: `frontend/scripts/dead-code-baseline.json` no longer lists the removed symbols and Knip
  passes with a **stricter** baseline (not a looser one).
- [x] AC6: A seeded-violation test proves the guard fires: writing a `blog_image_map` reference (or a
  deleted v1 symbol) into a temporary `*.py`/`*.ts`/`*.tsx` file under a scanned root makes the
  static test fail with a
  non-zero exit naming the file (AE-0180).
- [x] AC7: Live same-name symbols are preserved (`BlogPostFilters` type, editorial
  `useCarouselProject`, `mapBlogPostToDashboard`); typecheck proves it.
- [x] AC8: The AE-0423 read fail-safe is deleted (no legacy-markdown → v2 adapter, no
  `blog_v2_non_migrated_rows` metric) and a regression test proves a non-v2 read now fails closed
  with the standard error/404 rather than adapting. The prod `--verify` gate was SATISFIED on
  2026-10-19 (owner-run `blog_v1_to_v2 --verify` reported zero non-v2 rows, translations
  included); recorded in Test Evidence.

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
  removal) **and a prod `--verify` zero-non-v2 report — SATISFIED on 2026-10-19 (owner-run
  `--verify` = 0 non-v2 rows)**, AE-0424 (new image controls replace `ImageGenModal`); may run
  before/after AE-0426. AE-0422/AE-0423/AE-0424/AE-0425 (#146) and AE-0426 (#148) are merged
  into `main` (PR #149 is based on it, `1b59bee15`).
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

- [x] Security reviewed (no authz/URL behavior changed)
- [x] Code quality reviewed (no over-deletion of same-name live symbols)
- [x] Acceptance criteria validated
- [x] Edge cases tested (Knip baseline still passes; guard fires on a seeded violation)
- [x] Orphan/unfinished code checked (no dangling imports, no empty barrels)

## Progress Log

### 2026-10-18 17:05

Ticket created after the owner revision: drop `blog_image_map` and delete the blog-v1 dead code.
Updated: the carousel distribution helpers and the `blog_markdown` columns are live and excluded;
the dual-write upsert moved to AE-0422 (it would clobber v2); the delete-time detach stays.

### 2026-10-19 — implementation

- AC1: removed the key from model/schema/design/API routes and from the frontend schema/renderer.
- AC2: deleted the 16 dead frontend files (+2 tests) and their barrel exports; baseline 60 → 34.
- AC3: deleted `carousel/nodes/content/` and its unit test.
- AC4: added distribution text assertions to `test_editorial_distribution_pack.py` (PT + EN).
- AC5: regenerated `dead-code-baseline.json` (down-only).
- AC6: new `scripts/check_blog_v1_dead_code.py` + seeded rule-fires test, wired into both gate sets.
- AC7: `BlogPostFilters` type, editorial `useCarouselProject`, `mapBlogPostToDashboard` preserved.
- AC8: `read_document` is strict; adapter + metric + metric constant removed; callers map the error.

### 2026-10-19 — worker takeover: retarget to main

- The orchestrator retargeted PR #149 to `main` (the AE-0423/AE-0424 bases merged) and the branch
  was rebased onto `origin/main` (`c9aac8162`), keeping main's behaviour and re-applying only this
  PR's deletions. Conflict resolutions: `publishing/index.ts` / `blog/components/types.ts` /
  `blog/hooks/types.ts` (AE-0424 had re-added dead symbols — re-pruned), knip baseline and
  `openapi.json` regenerated.
- `read_document(content)` / `display_content(content)` re-applied at every call site
  (`api/dependencies/blog_document.py:107`, `api/routes/blog_post.py:215`,
  `api/schemas/public_blog_post.py:115`); grep shows no call site passes a second argument.
- **AC8 prod gate SATISFIED:** the owner ran `blog_v1_to_v2 --verify` on prod on 2026-10-19 and it
  reported zero non-v2 rows (translations included). The read fail-safe removal is therefore
  allowed; ticket, `deploy.yml` comments and the service docstring record this evidence.

### 2026-10-19 — second rebase: AE-0425 (#146) and AE-0426 (#148) merged into main

- Rebased onto `origin/main` (`1b59bee15`) after the CI diff-cover gate failed because main moved
  mid-run (the shallow CI fetch diffed against a main containing AE-0425's changes).
- The barrel conflict kept AE-0425's live "blog: generation" exports
  (`BlogGenerationStatus`, `CreateBlogFromCarousel`, `generateStandaloneBlogPost`,
  `isGenerationInProgress`, `GENERATION_TOPIC_*`) and re-pruned the v1 dead exports again.
- AE-0425 call-site check: `blog_generate_support.py` uses `parse_blog_content` directly and
  `has_article()` catches `InvalidBlogDocumentError` (no two-argument `read_document` remains);
  all src call sites are one-argument.
- `openapi.json` regenerated from the merged source: it now also reconciles the AE-0425 blog
  generation schemas that were missing from the stale committed artifact on main (174 component
  schemas; ticket-relevant removals unchanged).

### 2026-10-19 — diff-cover: handler-level read tests (tracing artifact on main)

- CI's `backend:diff-cover` failed on the two changed route lines
  (`routes/blog_post.py:215`, `routes/public_blog_post.py:114-116,119`). Reproduced on
  `origin/main` itself: coverage (both C and Python tracers) does not record lines after the
  first `await` inside these rate-limited HTTP handlers even though they execute (proven with a
  manual line tracer and by response assertions; a plain FastAPI probe and a direct handler call
  trace fine). This is a pre-existing toolchain artifact on main, not a real gap.
- Fix: new handler-level unit tests that call the read handlers directly (no HTTP transport):
  `tests/unit/api/test_blog_post_read_handler_ae0428.py` (valid v2 → parsed content; non-v2 →
  422 `blog_document_not_v2`) and `tests/unit/api/test_public_blog_post_handler_ae0428.py`
  (valid v2 → public detail; non-v2 → uniform 404). They prove the AC8 fail-closed mapping at
  the handler boundary and make diff-cover deterministic. Local `uv run diff-cover
  coverage.xml --fail-under=75` on the changed lines: **100% (0 missing)**.

## Files Touched

Backend — `blog_image_map` removal / strict read (AC1, AC8):
- `backend/src/rag_backend/domain/models/carousel.py`
- `backend/src/rag_backend/application/services/carousel_template/design.py`
- `backend/src/rag_backend/api/schemas/carousel.py`, `api/schemas/__init__.py`
- `backend/src/rag_backend/api/routes/carousels/media.py`, `api/routes/carousels/preview.py`
- `backend/src/rag_backend/application/services/blog/blog_document_service.py`
- `backend/src/rag_backend/domain/constants/blog_document.py`
- `backend/src/rag_backend/api/dependencies/blog_document.py`
- `backend/src/rag_backend/api/schemas/public_blog_post.py`
- `backend/src/rag_backend/api/routes/public_blog_post.py`, `api/routes/blog_post.py`

Backend — deleted `carousel/nodes/content/` package (AC3):
- `application/services/carousel/nodes/content/{__init__,blog_cleanup,core,json_utils,slides}.py`
- `backend/tests/unit/application/test_carousel_content.py`

Frontend — deletions (AC2):
- `src/modules/publishing/blog/components/{image-gen-modal,seo-preview,accessibility-checker,keyboard-shortcuts-help,blog-post-filters}.tsx`
- `src/modules/publishing/blog/components/public-post/blog-post-admin-panel.tsx` (+ test)
- `src/modules/publishing/blog/hooks/{use-accessibility-check,use-seo-analysis,use-editor-shortcuts,use-carousel-blog}.ts` (+ `use-carousel-blog.test.ts`) and the orphan `hooks/index.ts`
- `src/modules/publishing/blog/adapters/blog-post-adapter.ts` (+ test)
- `src/constants/editor-shortcuts.ts`, `src/constants/seo.ts`

Frontend — edits (AC1, AC2, AC7):
- `src/schemas/carousel.ts` (+ `carousel.test.ts`), `src/lib/public-blog.ts` (+ test)
- `src/lib/server-fetch.ts` (+ test), `src/constants/server-fetch.ts`
- `src/modules/publishing/index.ts`, `modules/publishing/blog/components/types.ts`,
  `hooks/types.ts`, `components/public-post/types.ts`
- `src/modules/carousel-presentation/{queries.ts,index.ts,queries.test.ts}`
- `src/modules/publishing/blog/components/public-post/blog-post-content.test.tsx`
- `src/scripts/eslint-no-img-rule.test.ts` (comment wording only)

Guard + gate wiring (AC6):
- `scripts/check_blog_v1_dead_code.py` (new)
- `backend/tests/unit/scripts_ci/test_check_blog_v1_dead_code.py` (new, rule-fires)
- `scripts/ci/gates.sh`, `.github/workflows/ci-gate.yml`

Config / docs / deploy:
- `backend/.importlinter` and `backend/pyproject.toml` (dropped the deleted package's entries)
- `frontend/src/modules/publishing/index.ts` (removed the stale `useCarouselBlogPosts` doc)
- `.github/workflows/deploy.yml` (cutover comments now state that AE-0428 removed the read
  fail-safe and that merge is gated on a prod `--verify` = 0)

Tests / fixtures / artifact:
- `backend/tests/features/blog_sections_ae0423.feature`
- `backend/tests/integration/test_blog_sections_api_ae0423.py`,
  `backend/tests/integration/test_presentation_safety_net.py`
- `backend/tests/unit/application/test_blog_document_service_ae0423.py`,
  `backend/tests/unit/application/test_editorial_distribution_pack.py`
- `backend/tests/unit/api/test_blog_post_read_handler_ae0428.py` (new),
  `backend/tests/unit/api/test_public_blog_post_handler_ae0428.py` (new)
- `backend/tests/snapshots/presentation/design.json`
- `frontend/tests/features/blog.feature`, `frontend/tests/features/blog_no_carousel_slides_ae0422.feature`
- `frontend/scripts/dead-code-baseline.json` (regenerated: 60 → 34)
- `frontend/scripts/check-schema-drift.mjs` (dropped the two deleted mappings)
- `docs/architecture/openapi.json` (regenerated with `scripts/export_openapi.py`)

## Test Evidence

Targeted backend (live Postgres, after the final AE-0423 rebase):
```
uv run pytest tests/unit/application/test_blog_document_service_ae0423.py \
  tests/integration/test_blog_sections_api_ae0423.py tests/integration/test_presentation_safety_net.py \
  tests/unit/application/test_editorial_distribution_pack.py \
  tests/unit/scripts_ci/test_check_blog_v1_dead_code.py
=> 92 passed
```

Targeted frontend:
```
npx vitest run src/lib/public-blog.test.ts src/lib/server-fetch.test.ts \
  src/modules/carousel-presentation/queries.test.ts \
  src/modules/publishing/blog/components/public-post/blog-post-content.test.tsx \
  src/schemas/carousel.test.ts
=> 5 files / 71 tests passed
```

Gate reproduction (full `gate-capture.sh` runs — real gate exit codes, no pipes — after the
2026-10-19 rebase onto `origin/main`):
```
backend:  19 PASS, 0 FAIL, 4 SKIP (test / diff-cover / migrations / schema-drift — Postgres-
          dependent; no local DATABASE_URL, CI runs them against the service container)
frontend: 18 PASS, 0 FAIL, 0 SKIP (includes the full frontend:test suite and frontend:build)
```
Backend targeted (sqlite in-memory per conftest): 109 passed (blog document service, editorial
distribution pack, guard rule-fires, blog document domain) + 40 passed (sections API integration,
presentation safety net). Frontend targeted: 5 files / 71 tests passed.

**Mutation is deferred to CI** per the orchestrator rule for this machine (no local `mutmut` /
mutation lane; CI's mutation gate is the source of truth). The full `backend:test` suite runs in
CI with the Postgres service.

AC8 **merge gate — SATISFIED (owner-run prod evidence, 2026-10-19)**: the orchestrator confirmed
the owner ran the prod verification on 2026-10-19 and
`python -m rag_backend.scripts.blog_v1_to_v2 --verify` reported **zero non-v2 rows** (translations
included). Removing the read fail-safe is therefore safe, and this PR records that evidence. Note
`deploy.yml` deliberately runs the cutover with `set +e` and **always** brings the stack up — but
that ordering is no longer the gate: the owner's `--verify` run above is. Fail-closed regression
tests (prove no adapter remains): `test_legacy_public_row_is_404` and
`test_editor_read_of_a_legacy_row_is_422` (detail `blog_document_not_v2`) in
`test_blog_sections_api_ae0423.py`, plus `TestStrictRead` in
`test_blog_document_service_ae0423.py`.

AC1 grep (AC1's own check):
```
grep -rn "blog_image_map" backend/src frontend/src --include='*.py' --include='*.ts' --include='*.tsx'  => (empty)
```

## QA Report

Pending.

## Decision Log

- **Handler-level read tests for the changed route lines.** The test toolchain on main does not
  record post-await lines of these rate-limited HTTP handlers in coverage (reproduced on main with
  both tracer cores; the lines provably execute). Rather than weaken diff-cover, the AC8 fail-closed
  mapping is additionally tested by calling the handlers directly — real behavior tests, and they
  make the gate deterministic.
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
- **Guard tokens are scoped.** `CarouselBlogI18nResponse` / `CarouselBlogWithDesignResponse` are
  still LIVE backend API schemas (returned by `api/routes/carousels/{media,preview}.py`); only the
  frontend duplicates were deleted. The guard therefore matches those two tokens on frontend paths
  only. The frozen carousel prompt YAML still mentions `blog_image_map`; the guard scans code
  extensions only.
- **AC8 gate satisfied with owner-run prod evidence.** On 2026-10-19 the owner ran
  `blog_v1_to_v2 --verify` on prod with exit 0 (zero non-v2 rows, translations included), so the
  read fail-safe removal is safe; the ticket, `deploy.yml` comments and the service docstring
  record this. The deploy job itself does NOT abort on a failed cutover (`set +e` + always
  `up -d`, because the fail-safe historically kept rows rendering), so deploy ordering is not
  evidence — the owner's `--verify` run is. The two API regression tests + `TestStrictRead`
  prove the code fails closed with no adapter.
- **OpenAPI artifact regenerated, not hand-edited.** `docs/architecture/openapi.json` is generated
  by `scripts/export_openapi.py`. The committed artifact on the base was already stale relative to
  the base source, so regenerating also reconciles pre-existing, unrelated additions (first the
  AE-0418 autopilot cover schemas, then — after the AE-0425 rebase — the blog generation schemas
  missing from main's artifact). The only ticket-relevant changes are the removal of
  `CarouselBlogImageMapEntry`, the `blog_image_map` property, and the moved generate-image
  description. Regeneration is also what makes `frontend:schema-drift` green after the Zod
  deletions; the two now-dead entries were dropped from `check-schema-drift.mjs`'s SCHEMA_MAP.
- **Mutation deferred to CI.** The worker machine cannot sustain the local mutation lane (memory);
  per the orchestrator, CI's mutation gate is the source of truth for this ticket.

## Risk & Size

- **Risk:** Medium — wide deletion surface with same-name live symbols; mitigated by grep/knip
  checks and typecheck.
- **Size:** M

## Blockers

None.

## Final Summary

Blog v1 is gone: `blog_image_map` is removed from the domain model, design payload, API schemas
and routes, and the frontend schema/renderer; the 16 dead publishing components/hooks/adapter/
constants and the unreferenced `carousel/nodes/content/` package are deleted (dead-code baseline
60 → 34); the AE-0423 legacy-read adapter and its metric are removed so a non-v2 row now fails
closed; and a scoped static guard (with an AE-0180 rule-fires test) prevents the symbols from
coming back. Distribution helpers and same-name live symbols are preserved and tested. On
2026-10-19 the branch was rebased onto `origin/main` (after the AE-0423/AE-0424 bases merged),
keeping main's AE-0424 behaviour and re-applying only this PR's deletions; the AC8 prod gate is
satisfied (owner-run `--verify` = 0 non-v2 rows on prod, 2026-10-19).
