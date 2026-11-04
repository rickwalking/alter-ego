# AE-0612 — The EN heading-case allowlist applies to the first visible word

Status: In Development
Tier: T1
Priority: Medium
Type: Bug
Area: Backend
Owner: Claude
Agent Lane: developer → qa → release
Branch: fix/ae-0612-heading-allowlist-inside-markup
Kanban Card: TBD
Created: 2026-11-04
Updated: 2026-11-04

## Goal

An EN heading that opens with an allowlisted lowercase token passes the heading-case check, with or
without inline markup, and no repair turns that token into `IPhone`.

## Problem

`_validate_en_heading_case` (`presentation_validation.py`) compared the whole raw heading with the allowlist:
`heading.strip() in policy.intentional_lowercase_allowlist`. Only a heading that is exactly `iPhone` matched.
So `iPhone tips` and `<strong>iPhone</strong> tips` reported `heading_not_sentence_case_en`, although
`sentence_case.py` documents that text opening with an allowlisted token "is never flagged nor rewritten", and
`_allowlisted_at` already implements that for the other casing rules.

The same gap sits in two repair paths that uppercase the first visible letter without knowing the allowlist:

| Path | Input | Before | Why |
|---|---|---|---|
| `slides_data_for_language` (EN render source) | heading or body `iPhone tips` | `IPhone tips` | runs on every EN export, with no violation needed |
| `deterministic_repair_slide_payload` | heading `iPhone tips`, lowercase item title | `IPhone tips` | an item title reports the same code, and the repair reads only the code |

Fixing the check alone would let the heading pass validation and still reach the slide as `IPhone tips`.

## Scope

- `opens_with_allowlisted` in `sentence_case.py`, on the existing `_first_significant_index` and `_allowlisted_at`.
- `_validate_en_heading_case` uses it in place of the whole-heading comparison.
- `repair_text_sentence_case_en` takes the allowlist, and the EN export passes the project policy's list.
- The heading repair ignores a heading-case code that an item title reported.

## Non-Goals

- The allowlist and its contents, the rule's severity, its EN-only scope and every other validator.
- `5 iPhone tips` (see Blockers / follow-ups).

## Acceptance Criteria

- [x] `<strong>iPhone</strong> tips`, nested tags, `iPhone tips` and `macOS` do not fire.
- [x] The rule still fires on a seeded lowercase heading, plain and wrapped in markup (rule-fires test).
- [x] `<strong>iphone</strong>` and `<strong>word</strong>` still fire: the match stays case-sensitive.
- [x] `iPhoneX` and a token that is only a prefix of a longer word still fire, plain and wrapped.
- [x] No repair rewrites a heading or body that opens with an allowlisted token, or a tag.
- [x] The allowlist is unchanged, and no new entry was needed.

## Gherkin Scenarios

`backend/tests/features/en_heading_case_allowlist_inside_markup_ae0612.feature`

```gherkin
Feature: The EN heading-case allowlist applies to the first visible word (AE-0612)

  Scenario: An allowlisted token wrapped in a strong tag passes
  Scenario: An allowlisted token under nested tags passes
  Scenario: A plain heading that opens with an allowlisted token passes
  Scenario: A heading that is only an allowlisted token still passes
  Scenario: A heading that has no visible text has no opening token
  Scenario: A plain lowercase heading still fires
  Scenario: A lowercase word wrapped in a strong tag still fires
  Scenario: The allowlist match stays case-sensitive
  Scenario: A token that is only the prefix of a longer word still fires
  Scenario: A token that is only the prefix of a wrapped longer word still fires
  Scenario: A token after the first visible word is not an opening token
  Scenario: The repair leaves a wrapped allowlisted heading as it is
  Scenario: The repair still fixes a lowercase heading next to a lowercase item title
  Scenario: The EN export keeps an allowlisted token in the heading and the body
  Scenario: The EN export still sentence-cases other lowercase copy
```

## Delta

### ADDED

- `opens_with_allowlisted` in `sentence_case.py`.
- `_slide_field_codes` in `presentation_copy_repair.py`.
- The feature file and `tests/unit/application/test_en_heading_case_allowlist_markup_ae0612.py`.

### MODIFIED

- `_validate_en_heading_case` matches the allowlist on the first visible word.
- `repair_text_sentence_case_en` and `slides_data_for_language` take an optional allowlist.
- `run_bilingual_export` passes the project policy's allowlist.
- `deterministic_repair_slide_payload` builds its codes through `_slide_field_codes`.

### REMOVED

- The whole-heading allowlist comparison.

## Affected Areas

- Backend: carousel presentation validation, deterministic repair and EN export.
- Frontend: none.
- Database: none.
- API: none.
- Tests: new unit file and feature.
- Docs: none in this PR.
- Prompts/LLM: none.
- Observability: none.
- Deployment: none.

## Dependencies

- Blocks: none.
- Blocked by: none.
- Related: AE-0605.

## Implementation Plan

1. Feature, then tests that fail on the current code.
2. Fix the check, the repair and the export.
3. Touched tests and cheap gates.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-11-04

Ticket created. Feature and tests written; 6 of 25 failed before the fix. Export wiring test added afterwards.
All 27 pass after the fix.

## Files Touched

- `backend/src/rag_backend/application/services/carousel/sentence_case.py`
- `backend/src/rag_backend/application/services/carousel/presentation_validation.py`
- `backend/src/rag_backend/application/services/carousel/presentation_copy_repair.py`
- `backend/src/rag_backend/application/services/carousel/types.py`
- `backend/src/rag_backend/application/services/carousel/nodes/export.py`
- `backend/tests/features/en_heading_case_allowlist_inside_markup_ae0612.feature`
- `backend/tests/unit/application/test_en_heading_case_allowlist_markup_ae0612.py`

## Test Evidence

- New tests: 27 passed (6 of the first 25 failed before the fix).
- Removing `_slide_field_codes` by hand makes the item-title repair test fail, so that guard has its own test.
- Every test file that imports the touched code: 974 passed.

## QA Report

Pending.

## Decision Log

- **A plain heading that opens with an allowlisted token is exempt.** `iPhone tips` passes, not only the wrapped
  form. The module doc of `sentence_case.py` already says so and the casing rules already behave that way, so the
  check now agrees with them. The allowlist contents do not change; only where the match happens does.
- **The repairs are in scope.** The acceptance criteria say no repair rewrites an allowlisted token, and both
  paths in the Problem table did. Without them a heading could pass the check and still render as `IPhone tips`.
- **The heading repair filters the code by field instead of taking the allowlist.** A heading that opens with a
  token no longer fires, so the only way to reach the repair was an item title's code. Filtering removes that path
  and keeps `deterministic_repair_slide_payload` at three arguments. A violation with no field still repairs.
- **The export loads the policy in `run_bilingual_export`.** `types.py` is a pure-data module, so it takes the
  allowlist as an argument. It defaults to empty, which keeps today's result for callers that pass none.
- **`presentation_validation.py` grows by 3 lines of import (415 to 418).** It was over the 400-line limit
  already. Splitting it is unrelated to this fix.

## Blockers

None.

Follow-ups, not done here:

- `5 iPhone tips` still fires, and the repair still returns `5 IPhone tips`, as it did before this ticket. The first
  visible word is `5`, so the token does not open the heading, and digits stay outside the exemption (AE-0605).
  Stopping the repair alone would leave a violation nothing can repair; exempting the heading widens the rule.
  Either one is a rule decision for the owner.
- `owner_autofix_fill.py` calls `capitalize_first_letter` without the allowlist on its generated item titles and
  bodies. It is not the heading path, so it is left as it is.

## Final Summary

Pending.
