# AE-0045 — Strategy and Chain-of-Responsibility for Presentation Logic

Status: In Development
Tier: T2
Priority: Medium
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: architect → developer → qa
Branch: feat/ae-0045-strategy-chain-presentation
Kanban Card: AE-0045
Created: 2026-06-10
Updated: 2026-06-10

## Goal

Replace the 6-branch if/elif chain in `_build_locale_presentation` with a dispatch table (lightweight Strategy), refactor the 3-tier fallback in `resolve_presentation_review_from_state` with Chain-of-Responsibility, and deduplicate the async/sync pair in `presentation_review.py`.

## Problem

PR #11 review flagged:
- `repair_workflow_malformed_drafts.py`: `_build_locale_presentation` has a 6-branch if/elif chain — "very long/complex function". Strategy pattern recommended.
- `presentation_review.py`: `resolve_presentation_review_from_state` has 3-tier fallback (validation → localized → slide_drafts) in 45 lines. `build_presentation_review_updates` and its `_async` variant share ~95% code.

## Scope

### Dispatch Table for `_build_locale_presentation`

Use a dictionary dispatch table (not full Strategy classes — the function is in a repair script):

```python
_BUILDERS: dict[str, Callable[[Mapping[str, object], str | None, int], dict[str, object]]] = {
    "intro": _build_intro,
    "summary": _build_summary,
    "content": _build_content,
    "closing": _build_closing,
}

def build_locale_presentation(slide_type, locale_data, *, tldr_strip=None, icon_offset=0):
    builder = _BUILDERS.get(slide_type, _build_cta)  # CTA is fallback
    return builder(locale_data, tldr_strip, icon_offset)
```

### Chain-of-Responsibility for `resolve_presentation_review_from_state`

```python
_RESOLVERS: list[Callable[[dict[str, object]], ReviewResolution | None]] = [
    _resolve_from_validation,
    _resolve_from_localized_slides,
    _resolve_from_slide_drafts,
]

def resolve_presentation_review_from_state(state):
    for resolver in _RESOLVERS:
        result = resolver(state)
        if result is not None:
            return result
    return None
```

### Async/Sync Dedup

Extract common logic in `build_presentation_review_updates`/`_async` to `_build_presentation_review_common()`. The async version `await`s only the repair call:

```python
async def build_presentation_review_updates_async(...):
    ctx = _build_presentation_review_common(...)
    ctx.localized = await repair_localized_slides(...)
    return _finalize_review(ctx)
```

## Non-Goals

- Changing the return types of any function
- Moving code between modules (in-function refactoring only)
- Changing tests beyond adding new ones

## Modularization Alignment (2026-06-12)

Wave B (after AE-0041) — pre-builds target architecture. Per the plan,
this work **belongs to carousel_presentation** (Phase 5):

- Colocate `_BUILDERS` and `_RESOLVERS` dispatch tables with the
  presentation code they serve; they become module-internal policy when
  Phase 5 extracts the module.
- `resolve_presentation_review_from_state` chain is future presentation
  domain policy — keep it free of FastAPI/SQLAlchemy imports now so the
  later move is a file move, not a refactor.
- Do not generalize the dispatch into a framework: the plan defers any
  generic `ContentFormatProducer` abstraction until a second format
  needs it.

## Acceptance Criteria

- [ ] `_build_locale_presentation` replaced with dispatch table (5 pure builder functions + dict)
- [ ] `resolve_presentation_review_from_state` uses Chain-of-Responsibility with 3 resolvers
- [ ] `build_presentation_review_updates` and `_async` share common logic via extracted `_build_presentation_review_common()`
- [ ] All existing tests pass without modification
- [ ] Each builder function is independently unit-testable
- [ ] Each resolver function is independently unit-testable
- [ ] Mutation-killing tests for: unknown slide_type, all resolvers return None, async/sync output parity

## Gherkin Scenarios

```gherkin
Feature: Dispatch Table for Slide Types

  Scenario: unknown slide_type falls back to CTA
    Given an unknown slide_type "bogus"
    When build_locale_presentation is called
    Then the CTA builder is used

  Scenario: intro builder returns correct structure
    Given slide_type "intro"
    When build_locale_presentation is called
    Then result has slide_type "intro" and heading

Feature: Chain-of-Responsibility

  Scenario: validation resolver succeeds first
    Given state with valid "presentation_validation" key
    When resolve_presentation_review_from_state is called
    Then the validation resolver returns the result
    And no other resolver is called

  Scenario: all resolvers return None
    Given state with no presentation data
    When resolve_presentation_review_from_state is called
    Then None is returned

Feature: Async/Sync Parity

  Scenario: sync and async produce same output
    Given identical inputs for sync and async variants
    When both functions complete
    Then their outputs are identical
```

## Delta

### MODIFIED

- `scripts/repair_workflow_malformed_drafts.py`
- `services/carousel/presentation_review.py`

### ADDED

- `_build_intro`, `_build_summary`, `_build_content`, `_build_closing`, `_build_cta` functions
- `_resolve_from_validation`, `_resolve_from_localized_slides`, `_resolve_from_slide_drafts` resolvers
- `_build_presentation_review_common()` shared logic

## Affected Areas

- Backend: 2 files
- Tests: Unit tests for builders, resolvers, and async/sync parity
- Docs: None
- Observability: None

## Dependencies

- Blocks: None
- Blocked by: AE-0041 (removes magic strings from same files first)
- Related: None

## Implementation Plan

1. Extract 5 builder functions from `_build_locale_presentation`
2. Create `_BUILDERS` dispatch dict; replace if/elif chain with dict lookup
3. Extract 3 resolver functions from `resolve_presentation_review_from_state`
4. Create `_RESOLVERS` list; replace fallback chain with iteration
5. Extract `_build_presentation_review_common()` from both async/sync functions
6. Refactor async function to `await` only the repair call
7. Add unit tests for each builder, resolver, and parity
8. Run full test suite

## QA Checklist

- [ ] Security reviewed — no auth changes
- [ ] Code quality reviewed — no magic strings
- [ ] Acceptance criteria validated
- [ ] Edge cases tested — unknown slide_type, empty state, all resolvers None
- [ ] Orphan/unfinished code checked — old function still callable as deprecated

## Progress Log

### 2026-06-10

Ticket created.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## High Risk Areas

<!-- AE-0050 safeguard tagging — feeds architect-skill skeptical-review trigger -->

- Risk level: **MEDIUM**
- Reason: presentation logic change — `resolve_presentation_review_from_state`
  refactored to Chain-of-Responsibility and the review-update builders share
  `_build_presentation_review_common`. Drives blocking presentation validation
  that gates content approval.
- Affected high-risk surfaces: carousel workflow (presentation review +
  validation gate), event emission (validation status feeds phase events),
  artifact paths (localized slides reference rendered slide images).
- Mitigation: public signatures unchanged (no wrapper needed); added pattern
  test coverage; source refactor entangled in commit `59980df` (see AE-0050
  rollback ledger).

## Decision Log

- Per architect validation: using dispatch table (not full Strategy classes) for the repair script to avoid overengineering. Full Strategy pattern would add 5+ classes for a script that may be temporary.

## Blockers

None.

## Final Summary

Pending.
