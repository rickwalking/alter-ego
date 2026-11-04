# AE-0605 — The EN heading-case check reads the first visible letter

Status: In Development
Tier: T1
Priority: Medium
Type: Bug
Area: Backend
Owner: Worker (Claude)
Agent Lane: developer → qa → release
Branch: fix/ae-0605-heading-case-leading-markup
Kanban Card: TBD
Created: 2026-11-04
Updated: 2026-11-04

## Goal

An EN heading that opens with inline markup is judged on its first visible letter, not on the tag.

## Problem

`_validate_en_heading_case` (`presentation_validation.py`) tests `first_cased_alpha(heading)`
(`presentation_validation_fields.py`, its only caller). That helper scans the raw text, so on
`<strong>Word ...` it returns the `s` of the tag and reports `heading_not_sentence_case_en`: a false
positive on a correct heading.

The same blind spot sits in the matching repair. `_repair_heading_sentence_case_en` uppercased the first
alphabetic character of the raw text, which is also inside the tag:

| Input | Check today | Repair today | Result |
|---|---|---|---|
| `<strong>Word</strong> x` | fires (false positive) | `<Strong>Word</strong> x` | a correct heading gets a corrupted tag |
| `<strong>word</strong> x` | fires | `<Strong>word</strong> x` | the tag is corrupted, the letter stays lowercase, and the check then passes on the `S` |

Both rows were reproduced by the new tests before the fix.

## Scope

- `first_cased_alpha` skips HTML tags, so the check reads the first visible letter. The content keeps its
  markup: only the check's view of the text changes.
- The heading repair capitalizes the first visible letter too, through the existing
  `repair_text_sentence_case_en`.
- `strip_html_tags` in `sentence_case.py`, on the tag pattern that module already uses.

## Non-Goals

- No change to the rule's severity, its EN-only scope or any other validator.
- Digits are not exempted: `5 tips` fires today and still does (see Decision Log).
- The allowlist test is unchanged (see Blockers / follow-ups).

## Acceptance Criteria

- [x] A heading that starts with `<strong>` and an uppercase letter passes.
- [x] The rule still fires on a real lowercase heading, plain and wrapped in `<strong>` (rule-fires
      regression test; nested tags too).
- [x] Edge cases: nested tags, closing tag plus whitespace, a heading that is only markup, a non-letter
      first character.
- [x] The tags stay in the content. The repair turns `<strong>word` into `<strong>Word` and never rewrites
      a tag.
- [x] Severity, EN-only scope and other validators are unchanged.

## Gherkin Scenarios

`backend/tests/features/en_heading_case_leading_markup_ae0605.feature`

```gherkin
Feature: The EN heading-case check reads the first visible letter (AE-0605)

  Scenario: A heading that starts with a strong tag and an uppercase letter passes
  Scenario: Nested tags before an uppercase letter pass
  Scenario: A closing tag and whitespace before an uppercase letter pass
  Scenario: A heading that is only markup has no letter to check
  Scenario: A plain lowercase heading still fires
  Scenario: A lowercase heading wrapped in a strong tag still fires
  Scenario: A lowercase heading under nested tags still fires
  Scenario: A non-letter first character keeps its current result
  Scenario: The rule stays EN-only
  Scenario: The repair capitalizes the visible letter and keeps the tag
  Scenario: An already correct wrapped heading is left as it is
```

## Delta

### ADDED

- `strip_html_tags` in `sentence_case.py`.
- The feature file and `tests/unit/application/test_en_heading_case_leading_markup_ae0605.py`.

### MODIFIED

- `first_cased_alpha` reads the text without its HTML tags.
- `_repair_text_field` calls `repair_text_sentence_case_en` for the EN heading.

### REMOVED

- `_repair_heading_sentence_case_en`.

## Affected Areas

- Backend: carousel presentation validation and deterministic repair.
- Frontend: none.
- Database: none.
- API: none.
- Tests: new unit file and feature.
- Docs: none.
- Prompts/LLM: none.
- Observability: none.
- Deployment: none.

## Dependencies

- Blocks: none.
- Blocked by: none.
- Related: none.

## Implementation Plan

1. Feature, then tests that fail on the current code.
2. Fix the check and the repair.
3. Touched tests and cheap gates.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-11-04

Ticket created. Feature and tests written; 7 of 17 failed before the fix, including the two repair tests.
All 17 pass after it.

## Files Touched

- `backend/src/rag_backend/application/services/carousel/sentence_case.py`
- `backend/src/rag_backend/application/services/carousel/presentation_validation_fields.py`
- `backend/src/rag_backend/application/services/carousel/presentation_copy_repair.py`
- `backend/tests/features/en_heading_case_leading_markup_ae0605.feature`
- `backend/tests/unit/application/test_en_heading_case_leading_markup_ae0605.py`

## Test Evidence

- New tests: 17 passed (7 failed before the fix).
- Every test file that imports the touched code: 759 passed.

## QA Report

Pending.

## Decision Log

- **The repair is in scope.** The brief's scope names the check, but fixing the check alone would leave
  `<strong>word` firing and being repaired to `<Strong>word`, which still fires: the old repair only "worked"
  because the check then read the `S` of the tag. A blocker that can no longer be repaired, plus a corrupted
  tag, is worse than the false positive, so the repair moves with the check. No validator changes.
- **`first_cased_alpha` is fixed instead of swapping in `starts_lowercase`.** `starts_lowercase` already skips
  tags, but it stops at a digit and exempts handles and URLs, so `5 tips` and `@handle` would stop firing.
  That would widen the rule's exemptions, which is out of scope.
- **Tags are skipped up to the first letter, not only at position 0.** `5 <strong>Tips` was the same false
  positive, and any tag before the first letter is leading markup.
- **The tag pattern is the one `sentence_case.py` already uses** (`<[^>]+>`), so the check and the repair
  agree on what a tag is.

## Blockers

None.

Follow-up, not done here: the allowlist test compares the whole raw heading, so `<strong>iPhone</strong>` still
fires where a bare `iPhone` does not. It fired before this ticket too (on the `s`). Changing it would change the
rule's exemptions, so it is left alone.

## Final Summary

Pending.
