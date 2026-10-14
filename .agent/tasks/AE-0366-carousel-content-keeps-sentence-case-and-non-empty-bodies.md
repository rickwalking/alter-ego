# AE-0366 — Carousel content keeps sentence case and non-empty bodies

Status: In Development
Tier: T2
Priority: P0
Type: Bugfix
Area: backend
Owner: Claude Code (claude-opus-5-5)
Agent Lane: developer → qa → release
Branch: fix/ae-0366-content-casing-and-body
Kanban Card: TBD
Created: 2026-10-14
Updated: 2026-10-14
Parent: AE-0348

## Goal

Carousel slides ship in normal sentence case (proper nouns kept) with visible copy under every
non-CTA heading, in PT and EN, and a reviewer's slide edits reach the rendered slides.
Deterministic guards catch any regression without depending on the model.

## Problem

Prod carousel `8e350d6e-78fc-436c-ab95-bed02535198b` (PT-BR, GLM 5.3): slide 4 rendered only a
title, slide 5's heading started lowercase with "argon" lowercased, slide 6 was all lowercase,
the persisted EN `translation_en` was fully lowercase with `<strong>` mangled into bare
`strong ... /strong`, and `presentation_validation` said `valid` with 0 violations. Reviewer
edits at the content gate never reached `carousel_slides`, so the JPGs kept the old copy.

Root causes (evidence in the PR and the tests):

1. `ContentDraftAgent.draft_slide` passed the outline title, key points, sibling context and
   previous draft through `sanitize_llm_input`, which lowercases and strips `< > ( )`. GLM got
   "a versão para robótica leva o argon ..." for a correctly cased outline title and echoed it.
2. `_build_translation_payload` sent the PT heading/body to the EN translator through the same
   sanitizer: lowercased, `<strong>` stripped to `strong`.
3. The v2 policy made the PT casing rules warnings, the bounded repair silently capitalized
   only `localized_slides` (so the report said `valid`), and the rows were persisted from the
   unrepaired drafts. No rule checked an empty body, items, or EN body casing.
4. The v5 content prompt never stated a PT casing rule nor required a body.
5. Edits applied in the graph only touched workflow state. The persist mapping also preferred
   the translator map over an edited `presentation_en` and fell back to stale `draft_text`.

## Scope

- Case- and markup-preserving `sanitize_model_copy` for the drafter inputs, the EN translation
  payload and the caption headings.
- Policy `hero_lower_third_v3` (new create-time version; v2 stays frozen): blocking sentence case
  in PT + EN for headings, bodies and structured items; objective rubric rules `body_empty`,
  `closing_actions_missing`, `summary_points_missing`, `translation_not_english`,
  `emphasis_markup_invalid`; configured proper nouns extended; the `quality_rubric` (single
  source of truth for prompt checklist + validator rule codes, loader-enforced).
- Safe deterministic repair before validation (first letter only, locale-safe, digit and
  allowlist aware; no proper-noun guessing) that records blocking `casing_repairs` markers, so
  the content goes back for regeneration (fail-closed retry, approval refusal, autopilot revise).
- Rows persisted with the repaired copy (both locales).
- Prompt `carousel/v6` (`content.yaml` + `slide_translations.yaml`) with casing/body rules and
  the rendered quality rubric + self-check; now the default for the drafter and the translator.
- Edit → persist: before the workflow resumes, edited `presentation_pt/en` copy is projected
  onto the slide rows (heading, body, features/actions, `translation_en`), images untouched; the
  draft title/draft_text follow the edited presentation copy; the persist mapping treats the
  presentation copy as the source of truth.

## Non-Goals

- No DB migration. No change to persona code (`PersonaAgent.enforce` still lowercases its input;
  reported as a follow-up) or autopilot image code.
- No re-drive of the prod run (owner action).

## Acceptance Criteria

- [x] Drafter prompt keeps the outline casing; translator payload keeps casing and `<strong>`.
- [x] Lowercase heading/body/item text in PT or EN is a BLOCKING violation (v3).
- [x] Empty body on intro/content (content: unless 3+ complete features), closing with <3
  actions, summary with <3 points: BLOCKING.
- [x] Repair capitalizes "a versão…" → "A versão…" and "à frente" → "À frente"; digits and the
  intentional-lowercase allowlist and per-slide-type exemptions are respected.
- [x] Prod-shaped drafts: content approval is refused (`presentation_validation_blocked`);
  each blocking slide is re-drafted once; a reviewer fix unblocks.
- [x] Every quality-rubric rule code has a validator that fires on a seeded violation.
- [x] An edit at content/design/final_review rewrites the persisted heading/body/features/
  `translation_en`; the rendered HTML shows the edit; image path/prompt/notes unchanged.
- [x] Draft `title` follows the edited `presentation_pt.heading`.
- [x] v2 projects keep their frozen semantics; v1 unaffected.
- [x] Python 3.11 import check.

## Gherkin Scenarios

`backend/tests/features/carousel_content_quality_ae0366.feature`

## Affected Areas

- Backend: carousel presentation validation/repair, persistence, drafter, translator.
- Prompts/LLM: `agents/prompts/carousel/v6/`.
- Tests: `tests/unit/application/test_content_quality_*_ae0366.py`,
  `test_edited_slide_persist_ae0366.py`.

## Dependencies

- Related: AE-0312 (v2 casing rules), AE-0309 (fail-closed chain), AE-0364/AE-0365.

## Progress Log

### 2026-10-14

Root cause traced in code; scope extended by the coordinator with the EN translation
lowercasing, the edit → persist gap and the quality rubric.

## Files Touched

See the PR.

## Test Evidence

See `.agent/reports/AE-0366.dev-summary.md`.

## QA Report

Pending.

## Decision Log

- New policy version v3 instead of editing v2 (contracts README rule: never modify an existing
  policy file). v2 projects (incl. 8e350d6e) keep warning-only casing.
- Proper nouns are never guessed; only the configured list is canonicalized.

## Blockers

None.

## Final Summary

Pending.
