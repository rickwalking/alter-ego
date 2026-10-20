# AE-0435 — Blog generation: EN stored in Portuguese + one 900 s budget kills finished runs

Status: Dev Complete
Tier: T1
Priority: P1
Type: Bug
Area: Backend
Owner: Claude (orchestrator brief `orch/ae0435-brief.md`, QA 2026-10-19 F-01 / F-02)
Agent Lane: developer → qa → release
Branch: feat/ae-0435-blog-en-gate-timeout
Kanban Card: TBD
Created: 2026-10-20
Updated: 2026-10-20

## Goal

A blog generation whose article is written never dies on a global wall clock, keeps the
images it already made, and never stores Portuguese as `translations.en`.

## Problem

QA 2026-10-19 (`/home/pmarins/alter-ego-qa/2026-10-19-qa-full/REPORT.md`):

- **F-01** — from-carousel post `ba37f6f9` failed at exactly `started_at + 900 s`
  (`generation_timeout`, recoverable, 0 of 7 images) although its article was stored; the
  images-only retry needed ~12 min for 7 images.
- **F-02** — `content.translations.en` of `ba37f6f9` and of rebuilt post `99886e71` is
  Portuguese; the EN gate scored it 85 (voice + repetition only, no language check).

### Evidence (prod, read-only, 2026-10-20)

Generation rows of the last 12 runs (`ai_generation_metadata.generation` vs
`content.quality.checked_at`):

| stage | observed |
|---|---|
| text (writer + both gates) | 37 s – 3 min 10 s normally; ~14.7 min for `ba37f6f9` attempt 1 (model queue shared with the concurrent 11-post rebuild) |
| images, per concurrency-2 wave | 135 – 224 s (gpt-image); 10-image posts spend 13–14 min on images |
| whole run, 10 images | `ec0c1285` 14 min 54 s, `e640b9e9` 14 min 28 s — 6 s / 32 s under the 900 s wall |

EN quality of every post with a scored EN: the **only** two posts with EN
`rewrite_passes: 1` (`ba37f6f9`, `99886e71`) are exactly the two Portuguese ones; every post
whose EN passed the voice gate without a rewrite kept English EN.

### Root cause (file:line on `origin/main` 4f811e6fd2)

- **F-01**: `blog_generation_service.py:130` wraps the WHOLE run (writer, both gates, every
  image) in `asyncio.timeout(BLOG_GENERATION_TIMEOUT_SECONDS=900)`
  (`domain/constants/blog_generation.py:84`). Images are attached only after the whole
  batch (`_pipeline` → `_attach`), so a timeout during the image stage discards every
  finished image.
- **F-02**: the EN voice gate (`blog_quality_gate.py`) scores the English text with the PT
  persona (`PersonaVoiceScorer`, Portuguese samples), which answers with Portuguese
  suggestions ("Trocar 'inference' por 'inferência' para manter o português consistente").
  When EN scores < 70, the v1 judge (`prompts/blog/v1/judge.yaml`) — never told the
  article's language — turns those into notes, and the v1 rewrite
  (`prompts/blog/v1/rewrite.yaml`: Portuguese persona samples + Portuguese notes) writes
  Portuguese. Nothing after the gate checks the language. The parser does not copy PT
  into EN (`agents/blog_writer/parsing.py:parse_draft` reads `en.sections` only).

## Scope

1. **Stage budgets** — text stage (writer + gates + EN repair):
   `BLOG_GENERATION_TEXT_TIMEOUT_SECONDS` (default 1800 s = 2× the worst observed text
   stage) → timeout fails the run as before (`generation_timeout`, recoverable, nothing
   stored). Images stage: `BLOG_IMAGE_WAVE_TIMEOUT_SECONDS` (default 360 s ≈ 1.6× the worst
   observed wave) × ceil(slots / `BLOG_IMAGE_CONCURRENCY`); on timeout the finished images
   are attached, every unfinished slot gets `image_timeout`, the run ends `partial` +
   recoverable, and the existing retry is images-only (article exists).
   `BLOG_GENERATION_TIMEOUT_SECONDS` is removed (prod `.env` does not set it).
2. **Deterministic EN language gate** (`blog_english_gate.py`) — after the EN quality gate,
   every EN section (heading + body) is checked with the carousel's `wrong_language_detail`
   (AE-0413/AE-0430; no model). Portuguese → retranslate the gated PT with the editor's
   PT → EN translation, at most `BLOG_EN_MAX_RETRANSLATIONS = 2` (a failed call counts);
   an English retranslation is scored + scanned and stored. Still Portuguese → the article
   is stored **without** `translations.en`, images still run, the run ends `partial` with
   `en_translation_wrong_language` (recoverable). The owner then uses the editor's
   "Generate EN translation".
3. **Root-cause fix** — writer prompts `v2` (`prompts/blog/v2/`, `PROMPT_VERSION = "v2"`):
   judge + rewrite are told the language to keep and to ignore language-switching
   suggestions; draft says the `en` article is English only. The quality gate discards an
   EN rewrite that switched to Portuguese and keeps the pre-rewrite English sections.
   The editor's `BlogTranslationService` refuses a Portuguese answer
   (`blog_translation_wrong_language`, 502 on the route) so EN is never Portuguese there
   either.
4. **One-shot repair** — `python -m rag_backend.scripts.regenerate_blog_en` (default:
   read-only scan) / `--apply --only <post-id>` (translate PT, replace only
   `translations.en` through the versioned slot-write path; PT, images, cover unchanged).

## Non-Goals

- Making `PersonaVoiceScorer` language-aware (shared `PersonaAgent.evaluate_match`); the v2
  prompts + the deterministic gate neutralise its Portuguese suggestions for EN.
- An automatic EN repair on the images-only retry (the editor action covers it).
- Running the repair on prod (orchestrator, after deploy).

## Acceptance Criteria

- [x] AC1: the text stage and the images stage have separate budgets; the images budget is
  per wave × ceil(slots / concurrency) and is not reduced by the text stage's time.
- [x] AC2: a text-stage timeout ends `failed` / `generation_timeout` / recoverable with
  nothing stored.
- [x] AC3: an images-stage timeout keeps and attaches the finished images, marks each
  unfinished slot `image_timeout`, ends `partial` + recoverable (retry = images-only).
- [x] AC4: an EN that reads as Portuguese is detected without a model and retranslated
  (bounded, failed calls count); Portuguese is never stored as `translations.en`; after the
  retries the run ends `partial` with `en_translation_wrong_language` and images still run.
- [x] AC5: the cause is fixed: v2 judge/rewrite/draft prompts keep the language; an EN
  rewrite into Portuguese is discarded.
- [x] AC6: the editor translation refuses a Portuguese answer.
- [x] AC7: a read-only scan lists affected posts; `--apply --only` repairs only that post's
  EN (versioned write).
- [x] AC8: backend gates (except mutation) green locally; CI green (see PR).

## Gherkin Scenarios

`backend/tests/features/blog_generation_en_gate_timeout_ae0435.feature`

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests
- [x] Docs (ADR-0025 execution note, blog document model, `.env.example`)

## Dependencies

None. Shares `blog_generation_service.py` / `blog_quality_gate.py` with no other open ticket.

## Operational steps (after deploy; orchestrator)

1. Read-only scan (prod, 2026-10-20 pre-deploy run of the same detector: 28 posts with EN,
   2 affected — `ba37f6f9`, `99886e71`, 6/6 sections each):

   ```bash
   ssh root@206.189.180.85 'cd /opt/alter-ego && docker compose -f docker-compose.prod.yml exec -T backend python -m rag_backend.scripts.regenerate_blog_en'
   ```

2. Regenerate only the EN of `99886e71` (and of the QA post `ba37f6f9` if wanted):

   ```bash
   ssh root@206.189.180.85 'cd /opt/alter-ego && docker compose -f docker-compose.prod.yml exec -T backend python -m rag_backend.scripts.regenerate_blog_en --apply --only 99886e71-fcd2-4095-a023-ffb5fc278ce1'
   ```

   Re-run step 1: `wrong_en` must drop by one.

## Progress Log

### 2026-10-20

Root cause traced (prod rows + code), Gherkin, stage budgets, EN language gate, v2
prompts, editor translation guard, repair command, tests.

## Files Touched

- `backend/src/rag_backend/application/services/blog/{blog_generation_service,blog_generation_job,blog_generated_document,blog_image_batch,blog_quality_gate,blog_quality_scan,blog_translation_service}.py`
- new: `application/services/blog/{blog_english_gate,blog_en_repair}.py`,
  `bootstrap/blog_en_repair.py`, `scripts/regenerate_blog_en.py`,
  `agents/prompts/blog/v2/{system.md,draft.yaml,judge.yaml,rewrite.yaml,README.md}`
- `agents/blog_writer/{agent,constants}.py`, `bootstrap/blog_generation.py`,
  `domain/constants/{blog_generation,blog_editor}.py`, `domain/protocols/blog_generation.py`,
  `infrastructure/config/settings.py`, `backend/.env.example`
- docs: ADR-0025 execution note, `docs/architecture/blog-post-document-model.md`
- tests: `tests/features/blog_generation_en_gate_timeout_ae0435.feature`,
  `tests/unit/application/test_blog_{en_gate,stage_budget,en_repair}_ae0435.py`,
  `tests/unit/bootstrap/test_blog_en_repair_store_ae0435.py`, fakes + AE-0425 tests updated
  (English EN fixture, new timings)

## Test Evidence

- New tests: `test_blog_en_gate_ae0435.py` (17), `test_blog_stage_budget_ae0435.py` (10),
  `test_blog_en_repair_ae0435.py` (12), `test_blog_en_repair_store_ae0435.py` (3).
- Every backend gate except mutation, run one by one (`gates.sh backend:<gate>`, DB gates on
  a throwaway `postgres:16-alpine`): 21 PASS, 0 FAIL; full suite 6024 passed / 2 skipped;
  diff-cover 100% (235 changed lines). Python 3.11 import check OK.
  mutation: deferred to CI. Details + GATES_JSON: `.agent/reports/AE-0435.dev-summary.md`.
- Detector on prod data (read-only dump, 2026-10-20): 28 posts with EN → exactly
  `ba37f6f9` and `99886e71` flagged (6/6 sections), 0 false positives.

## QA Report

Pending.

## Blockers

None.
