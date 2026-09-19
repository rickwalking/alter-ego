# AE-0347 — Carousel blog body is an H1-only stub: long_form_notes never requested, research never fed, titles never set, non-public carousels leak publicly

Status: In Development
Tier: T2
Priority: High
Type: Bugfix
Area: Backend/LLM
Owner: Claude
Agent Lane: developer → qa → release
Branch: feat/carousel-blog-body-fix
Kanban Card: TBD
Created: 2026-09-19
Updated: 2026-09-19

## Goal

Carousel-origin blog posts carry a real body (research intro + one section per
slide of long-form prose) with a localized title in PT and EN, and never show up
on the public blog surface before the carousel is released.

## Problem

Diagnosed on prod project `dcaa5fef` (blog row `9817ec2b`) on 2026-09-19: the
stored blog is one line (`# <raw English topic>`) in both languages. Every one
of the 15 most recent carousel-origin `blog_posts` rows (2026-06-18 → 2026-09-14)
has a 14–137 char body and zero `##` sections. Four independent defects:

1. AE-0032 (2026-06-09) switched blog composition to per-slide `long_form_notes`,
   but `carousel/v3` and `carousel/v4` `content.yaml` return
   `{draft_text, confidence_score, sources_used, icon_name?}` — the field is
   parsed but **never requested**, so the composer skips every slide. The EN
   translation prompt likewise translated heading/body only.
2. `phase_artifact_runner._build_distribution` read `state["research_summary"]`,
   which **nothing writes**; research lives in `research_findings`.
3. The editorial path never calls `set_title`/`set_title_en`, so the H1 in BOTH
   languages is the raw `topic`.
4. `carousel_blog_dual_write` stamps every carousel blog `published` at compose
   time; `/api/public/blog-posts` filters on status only → blogs of carousels
   with `is_public=false` are listed and served (200) anonymously.

## Scope

- New `carousel/v5/content.yaml` (v4 + mandatory `long_form_notes`); agent → v5.
- `PROMPT_EDITORIAL_SLIDE_TRANSLATIONS` + payload/parse carry `long_form_notes`
  (case-preserving sanitizer).
- `research_summary_from_findings()` joins de-duplicated per-source summaries.
- `_ensure_blog_titles()` derives PT/EN titles from the intro slide when unset.
- `public_blog_visibility_clause()` (publishing facade) gates carousel-origin rows
  on the parent carousel's `is_public`; both public routes use it.

## Non-Goals

- Regenerating existing prod blogs (needs a content re-run per project).
- Changing the dual-write status semantics (read-time gate fixes existing rows).
- Excerpt / SEO meta / featured image for carousel blogs (separate ticket).

## Acceptance Criteria

- [x] WHEN the content agent drafts a slide THE SYSTEM SHALL render `carousel/content@v5`, which requires `long_form_notes`, and keep it on the draft.
- [x] WHEN slides are translated THE SYSTEM SHALL send PT `long_form_notes` and parse EN `long_form_notes` back.
- [x] WHEN the distribution pack builds THE SYSTEM SHALL open the blog with the de-duplicated `research_findings` summaries (empty/malformed → no intro, no error).
- [x] WHEN the project has no title/title_en THE SYSTEM SHALL set them from the intro slide heading / its EN translation, never overwriting existing titles.
- [x] WHEN an anonymous client reads `/api/public/blog-posts[/{id}]` THE SYSTEM SHALL hide carousel-origin rows whose carousel is not public (404 / absent) and keep standalone + public-carousel rows.

## Gherkin Scenarios

See `backend/tests/features/carousel_blog_body_ae0347.feature`.

## Affected Areas

- Backend: yes
- Frontend: no
- Database: no
- API: no (behaviour of public reads only)
- Tests: yes
- Docs: prompt README v5
- Prompts/LLM: yes
- Observability: no
- Deployment: no

## Dependencies

- Related: AE-0032, AE-0163, AE-0297, AE-0291

## Implementation Plan

1. v5 prompt + constant + agent wiring.
2. Translation contract.
3. Research summary + titles in the distribution pack.
4. Public visibility clause via the publishing facade.
5. Feature file + unit/integration tests.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-09-19
Diagnosed on prod; implemented on `feat/carousel-blog-body-fix` (worktree off main).
External QA r1 (GLM 5.2 via OpenCode, `.agent/reports/.external-review-ae0347.r1.stdout.log`):
VERDICT PASS, 2 MAJOR + 5 MINOR. Fixed M1 (notes now case-preserving-sanitized at
the source in `ContentDraftAgent._parse_draft`, agents layer — the application
layer cannot add an `agents` import under the DDD ratchet), M2 (warning log when
the model omits `long_form_notes`), m1 (`BlogPostOrigin` enum), m2 (translation
index falls back to position), m3 (intro slide selected by resolved index 1),
m4 (runner test proves `research_findings` → `research_summary` wiring).
m5 (translation prompt lives in a `.py` constant) left as-is: moving it to the
registry is a separate application→agents boundary change (see
[[prompt-registry-ddd-boundary]]).

## Files Touched

- backend/src/rag_backend/agents/prompts/carousel/v5/{content,outline}.yaml, README.md
- backend/src/rag_backend/domain/constants/carousel.py, ai_agents.py
- backend/src/rag_backend/agents/content_draft_agent.py
- backend/src/rag_backend/application/services/carousel/{blog_composition,editorial_distribution_generation,editorial_distribution_pack,phase_artifact_runner}.py
- backend/src/rag_backend/modules/publishing/{__init__,public}.py, infrastructure/public_visibility.py
- backend/src/rag_backend/api/routes/public_blog_post.py
- backend/tests/features/carousel_blog_body_ae0347.feature
- backend/tests/unit/application/test_carousel_blog_body_ae0347.py
- backend/tests/integration/test_public_blog_api_ae0297.py

## Test Evidence

Pending gate capture.

## QA Report

Pending.

## Decision Log

- Read-time `is_public` gate instead of changing dual-write status: fixes the
  already-stamped prod rows without a data migration.
- Titles derived deterministically from the intro slide (no extra LLM call).
- No bounded re-roll when notes are missing (QA M2): logged instead; a retry is
  an LLM-cost decision for a follow-up.

## Blockers

None.

## Final Summary

Pending.
