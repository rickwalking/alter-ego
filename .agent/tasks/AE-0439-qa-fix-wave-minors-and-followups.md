# AE-0439 — QA 2026-10-19 fix wave: minors F-07/F-12/F-13/F-14 + #154/#155 follow-ups

Status: Dev Complete
Tier: T1
Priority: P1
Type: Bug
Area: Backend
Owner: Worker (deepseek-v4-pro)
Agent Lane: developer → qa → release
Branch: feat/ae-0439-minors-and-followups
Kanban Card: TBD
Created: 2026-10-20
Updated: 2026-10-20

## Goal

Eight small root-cause fixes from the full 2026-10-19 QA wave (evidence:
`~/alter-ego-qa/2026-10-19-qa-full/REPORT.md`, read-only) plus the review
follow-ups recorded for PRs #154 (AE-0433) and #155 (AE-0434) in the
orchestrator queue (`~/alter-ego-qa/orch/QUEUE.md` line 43).

## Problem

- **F-07:** the create wizard never sends `slide_count` for Radar IA, so it is
  stored `NULL` (`resolved_slide_count()` returns `None` for news). The blog's
  section count then falls back to the legacy `slides_config`
  (`"1 intro, 3 content, 1 closing, 1 cta"` = 6), so a 7-slide deck
  (`7acaf967`) got 6 sections. Prod check (read-only): the v4 contract's
  `slide_count` 7/8 includes the CTA slide.
- **F-12:** carousel `persona_scores` stored `slide_1.overall` as 8.5 (raw
  0-10 judge answer) while slides 3-7 were 0-100 (prod checkpoint
  `7acaf967`, channel `persona_scores`, versions 12+ — decoded with
  msgpack). The read path rescales, so no gate effect, but the stored value
  is inconsistent. The write boundary must normalize to 0-100.
- **F-13:** `GET /api/carousels/{id}/workflow/state` `image_assets` exposes
  container paths (`/app/output/carousels/.../images/slide_1.jpg`).
- **F-14:** anonymous draft-image 404 from `GET /blog-images/{post}/{file}`
  carries no `Cache-Control`; the edge caches it (observed
  `max-age=14400`), so a 404 can linger up to 4 h after a publish.
- **#155(a):** other missing-image cases still surface as
  `image_decode_timeout`; the decode script reports every `img.decode()`
  rejection as a timeout, hiding a missing/broken file.
- **#154(A):** content-generation persona scoring (`_score_slides`) calls
  `judge_voice` without a fallback judge, so both attempts hit the slow
  first model of the queue (the AE-0433 fallback exists only in the slide
  fix).
- **#154(B):** a stale PASSING score is trusted after an unscored rewrite:
  the pending `rescore_pending` marker is ignored by the gate read, the
  content gate passes on the stale score, and the pending slide is never
  re-scored (AC3 only fires when the gate fails).
- **#154(C):** the WAIT check is loose: `_judge_pending` trusts
  `reason == persona_score` even when the gate also fails on forbidden
  phrases / blocking quality rules / an engine refusal (the content policy
  returns the persona reason first), so such runs hang in WAIT instead of
  escalating.

## Scope

- Backend only. Shared files touched minimally (see Files Touched).

## Non-Goals

- The F-01/F-02 blog generation timeout and the EN language gate (AE-0435),
  label leaks (AE-0436), closing actions (AE-0437), editor F-05/F-08/F-11
  (AE-0438) and the 401 stream loop (AE-0440).
- The rebuild-script follow-ups (deferred in QUEUE.md).
- Any prod operation (read-only prod queries were used for evidence).

## Acceptance Criteria

- [x] AC1 (F-07): a Radar IA create request without `slide_count` stores 7
      (the v4 contract default, CTA included); an explicit 7 or 8 is kept.
- [x] AC2 (F-07): `resolve_section_count` prefers the real deck size (slide
      rows count) over `slides_config` when `slide_count` is null, so a
      7-slide deck yields 7 sections. The CTA slide counts as a section
      (documented in ADR-0025).
- [x] AC3 (F-12): the carousel content-scoring write path stores every
      persona-score entry on 0-100 (`overall` by itself, sub-scores
      together), reusing `domain/persona_score.py` helpers; old raw rows
      still read scaled.
- [x] AC4 (F-13): the workflow-state response (and the SSE review gate
      payload) maps `image_assets` container paths to
      `/api/carousels/{id}/preview/images/{file}`; non-path values pass
      through.
- [x] AC5 (F-14): every 404 of `GET /blog-images/...` carries
      `Cache-Control: no-store`; published/author responses keep their
      existing headers.
- [x] AC6 (#155a): a missing/broken image reports `image_load_failed`, a
      real race timeout keeps `image_decode_timeout`, other decode
      rejections keep `image_decode_failed`.
- [x] AC7 (#154A): the content-generation judge retry runs on the role
      queue's next model (fallback judge), like the slide fix.
- [x] AC8 (#154B): a gate that passes on a stale score with
      `rescore_pending` slides does not approve: the step re-scores the
      pending slides (no rewrite) and WAITs until they are scored or the
      judge is declared unavailable.
- [x] AC9 (#154C): the WAIT fires only when the persona reason is the sole
      failure; a forbidden hit / blocking quality rule / engine refusal
      alongside it escalates.
- [x] AC10: Gherkin + unit tests reference the scenarios; backend gates
      green locally (except mutation per machine limits); CI green.

## Gherkin Scenarios

`backend/tests/features/blog_carousel_minors_ae0439.feature`

- A Radar IA create without slide_count stores 7
- A blog from a 7-slide deck without a stored slide_count gets 7 sections
- Stored persona scores are on 0-100 even for a raw 0-10 judge answer
- The workflow state maps image_assets to owner preview URLs
- An anonymous draft blog image 404 is never cached
- A missing image reports image_load_failed, not a decode timeout
- The content-generation judge retries on the queue's next model
- A passing gate with pending re-scores waits instead of approving
- A wait fires only when the voice floor is the sole failure

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests
- [x] Docs (ADR-0025 clarification)

## Dependencies

None. Related: AE-0407, AE-0433, AE-0434, AE-0435, ADR-0025.

## Decisions

- **The CTA slide counts as a section.** The v4 contract's `slide_count`
  (7/8) includes the CTA slide, POV stores 9 including its CTA, and
  ADR-0025's rule is "one section per slide". ADR-0025 §Count updated.
- **Radar IA default `slide_count` is 7** (`NEWS_SLIDE_COUNT_MIN`), the
  contract's `slide_count_default`; an explicit 8 (twist) is still
  accepted.
- **F-12 normalization happens at the write boundary** (`_score_slides`)
  with a new pure `persona_score.on_hundred_scale_entry` helper, so any
  judge dict (whatever model/prompt variant produced it) is stored on
  0-100. The read path (`stored_overall`) already rescales old rows.
- **F-13 converts at the response boundary**, never in the stored state:
  the autopilot image gate keeps reading the raw paths.
- **#154(B) re-scores pending slides in the existing fix loop**: pending
  slides join `select_targets` at the content gate with no issues, so
  `fix_slide` re-scores without a rewrite and the existing
  `rescore_pending`/tick machinery (bounded escalation) is reused.

## Progress Log

### 2026-10-20

Evidence gathered (prod read-only checkpoint decode + QUEUE.md follow-ups);
ticket and Gherkin written; all nine fixes implemented with tests; backend
gates green (21/21 locally, mutation deferred to CI); PR opened.

## Files Touched

- `backend/src/rag_backend/api/schemas/carousel_content_mode.py`
- `backend/src/rag_backend/application/services/blog/blog_section_plan.py`
- `backend/src/rag_backend/api/routes/blog_generate_support.py`
- `backend/src/rag_backend/infrastructure/database/blog_rebuild_materials.py`
- `backend/src/rag_backend/domain/persona_score.py`
- `backend/src/rag_backend/application/services/carousel/phase_artifact_runner.py`
- `backend/src/rag_backend/domain/constants/blog_editor.py`
- `backend/src/rag_backend/api/routes/blog_post_images.py`
- `backend/src/rag_backend/application/services/carousel/design_token_utils.py`
- `backend/src/rag_backend/api/routes/carousels/editorial_workflow_routes_response.py`
- `backend/src/rag_backend/application/services/carousel/editorial_workflow_sse_build.py`
- `backend/src/rag_backend/infrastructure/external/playwright_geometry_scripts.py`
- `backend/src/rag_backend/domain/constants/playwright_geometry.py`
- `backend/src/rag_backend/modules/autopilot/domain/gate.py`
- `backend/src/rag_backend/modules/autopilot/domain/snapshot.py`
- `backend/src/rag_backend/application/services/carousel/slide_fix_targets.py`
- `backend/src/rag_backend/modules/autopilot/application/slide_autofix.py`
- `docs/decisions/0025-blog-post-owns-structure-voice-and-images.md`
- `backend/tests/features/blog_carousel_minors_ae0439.feature` (new)
- `backend/tests/unit/domain/test_persona_score_ae0439.py` (new)
- `backend/tests/unit/application/test_blog_section_plan_ae0439.py` (new)
- `backend/tests/unit/application/test_content_scoring_ae0439.py` (new)
- `backend/tests/unit/application/test_editorial_sse_image_assets_ae0439.py` (new)
- `backend/tests/unit/api/test_blog_post_images_ae0439.py` (new)
- `backend/tests/unit/api/test_editorial_workflow_routes_response.py`
- `backend/tests/unit/infrastructure/test_playwright_geometry.py`
- `backend/tests/unit/modules/autopilot/test_unscored_judge_step_ae0433.py`
- `backend/tests/unit/modules/autopilot/test_gate_snapshot.py`
- `backend/tests/unit/application/test_unscored_judge_ae0433.py`
- `backend/tests/integration/test_carousel_content_mode_api.py`
- `backend/tests/integration/test_carousel_workflow_safety_net.py`
- `backend/tests/integration/carousel_consolidation/test_workflow_validation.py`
- `backend/tests/snapshots/editorial/_snapshot.py` + `workflow_state.json` + `workflow_start.json`

## Test Evidence

Every backend gate except mutation, each via
`bash scripts/ci/gate-capture.sh backend:<gate>` (never piped), on a local
Postgres container (DATABASE_URL set) so the DB gates really ran:

- format, lint, lint-diff, blanket-ignore, strict-diff, type (mypy strict),
  imports, arch-ratchet, docstrings, dead-code, inline-prompts, redis-factory,
  autopilot-env, healthcheck-loopback, bandit, pip-audit, integrity, test,
  diff-cover, migrations, schema-drift = **21 PASS** (0 fail, 0 skip).
- `backend:test` (full suite + coverage with Postgres): **6016 passed,
  2 skipped** (both pre-existing skips).
- New/updated tests: 152 across the AE-0439 files + the updated integration
  contracts; the AE-0434-style JS decode harness runs the real
  `IMAGE_DECODE_SCRIPT` under Node (present on this machine and on the CI
  ubuntu runners).
- Python 3.11 (prod image): all changed modules `py_compile` clean.
- Mutation: deferred to CI (never run locally; memory rule).
- Full `GATES_JSON` in `.agent/reports/AE-0439.dev-summary.md`.

## QA Report

Pending.

## Blockers

None.
