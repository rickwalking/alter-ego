# AE-0289 — preserve case when sanitizing edited slide copy

Status: Review
Tier: T1
Priority: P1
Type: Bugfix
Area: backend
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: fix/ae-0289-edited-slides-preserve-case
Created: 2026-07-01
Updated: 2026-07-01

## Problem

Submitting `structured_feedback.edited_localized_slides` to `/workflow/resume`
ran the final published slide copy through `sanitize_llm_input`, which
**lowercases** text (it exists to harden strings fed back into an LLM prompt).
That corrupted headings, so approve failed with 422
`heading_not_sentence_case_en` — the edited-slides path could never publish valid
copy. Discovered while fixing prod carousel `a2991a39` (AE-0288 follow-up).

## Fix

- `agents/input_sanitizer.py`: new `sanitize_display_input` — same injection
  defenses as `sanitize_llm_input` (strip `< > ( )` + `INJECTION_PATTERNS`, cap
  length) but **case-preserving** (patterns matched case-insensitively).
- `api/routes/carousels/editorial_workflow_routes_sanitize.py`:
  `_sanitize_payload_strings` (edited-slide presentation copy) uses it.
  `sanitize_llm_input` (LLM-prompt paths) is unchanged; `slide_type` stays lower.

## Acceptance Criteria

- [x] Edited-slide headings/bodies keep case after sanitization.
- [x] Injection patterns + `< > ( )` still stripped; length still capped.
- [x] `sanitize_llm_input` (LLM prompt path) unchanged (still lowercases).
- [x] Edited slides with proper-cased EN headings validate (no
      `heading_not_sentence_case_en`) on approve.
- [x] `gates.sh backend` green + external QA.

## Gherkin / Tests

`tests/unit/agents/test_input_sanitizer.py` (case preserved + injection stripped +
truncation), `tests/unit/api/test_editorial_workflow_routes_sanitize.py`
(edited-slide headings keep case).

## Files Touched

- `agents/input_sanitizer.py`, `editorial_workflow_routes_sanitize.py`, + 2 tests.

## Test Evidence

`gate-capture.sh backend` → 15 PASS / 0 FAIL / 4 SKIP; full suite 2467 passed.
Local repro: edited slides now sanitize with case intact and validate
`blocking:False`. See `.agent/reports/AE-0289.qa.md`.

## QA Report

See `.agent/reports/AE-0289.qa.md`.

## Final Summary

Edited-slide copy is now sanitized case-preservingly, unblocking the
edited-localized-slides approve path (used to fix a2991a39 without regenerating
images). Security defenses unchanged; only the LLM-prompt lowercasing removed for
final display content.
