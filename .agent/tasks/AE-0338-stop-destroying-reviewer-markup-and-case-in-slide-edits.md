# AE-0338 — stop destroying reviewer markup and case in slide edits

Status: Ready
Tier: T2
Priority: High
Type: Bug
Area: Backend
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-09-15
Updated: 2026-09-15

## Goal

Reviewer-authored slide copy must survive the round trip intact — markup renders
as markup, capitals stay capital — while prompt-injection protection stays in
place for text that is actually fed to an LLM.

## Problem

Reviewer edits are passed through `sanitize_llm_input`
(`backend/src/rag_backend/agents/input_sanitizer.py:11`), which is built for
*prompt inputs*, not for final published copy:

```python
cleaned = value.replace("<", "").replace(">", "").replace("(", "").replace(")", "")
lowered = cleaned.lower()
for pattern in INJECTION_PATTERNS:
    lowered = lowered.replace(pattern, "")
cleaned = lowered[:MAX_LLM_INPUT_LENGTH]     # line 17 — the lowercased text wins
```

Two destructive effects on reviewer text:

1. **Markup is stripped to literal words.** `<strong>bold</strong>` becomes
   `strongboldstrong` — the angle brackets are deleted, so the tag text survives
   as prose. Parentheses go the same way.
2. **Everything is lowercased.** Line 17 assigns the *lowered* string back to
   `cleaned`, so the returned value has lost all capitalization. AE-0289 already
   recognized this for published copy and added `sanitize_display_input`, which
   preserves case — but the slide-edit path still reaches the LLM-input variant.

Live consequences on carousel `dcaa5fef…`: markup had to be avoided entirely, and
because an edit **replaces the whole `presentation_pt`/`presentation_en` dict**,
every field must be resent on every edit or the omitted ones are lost. The
operator had to validate offline first
(`validate_localized_slides(..., policy_version="hero_lower_third_v1")`, where
budgets count tag characters) to avoid a rejected write.

## Scope

- Route reviewer/slide-edit text through `sanitize_display_input` (case-preserving)
  rather than `sanitize_llm_input`; audit every call site that handles
  human-authored **final copy**.
- Define the allowed inline markup for slide copy (e.g. `<strong>`, `<em>`) and
  sanitize by **allow-list escaping** rather than character deletion, so
  disallowed markup is escaped/rejected instead of silently turned into prose.
- Make budget counting consistent with the decision — state explicitly whether
  tag characters count toward a budget, and test it.
- Consider a partial-update (PATCH-semantics) shape for slide edits so omitting a
  field does not clear it; at minimum, document the replace-whole-dict behaviour
  in the API description and reject an update that would blank a required field.

## Non-Goals

- Weakening `sanitize_llm_input` itself — text genuinely sent to an LLM keeps its
  current protection.
- A rich-text editor in the frontend.
- Supporting arbitrary HTML in slides.

## Acceptance Criteria

- [ ] Reviewer-edited copy retains its capitalization end to end.
- [ ] `<strong>x</strong>` round-trips as markup (or is rejected with a clear
      error) — it never becomes the literal text `strongxstrong`.
- [ ] Disallowed markup is escaped or rejected, not silently deleted.
- [ ] Prompt-injection protection is unchanged for LLM-bound text (existing
      injection tests still pass).
- [ ] Budget counting behaviour for tag characters is documented and tested.
- [ ] An edit that omits a required field is rejected with a clear message rather
      than blanking it.

## Gherkin Scenarios

```gherkin
Feature: Reviewer copy survives sanitization

  Scenario: Capitalization is preserved
    Given the reviewer sets a heading to "Labs de Duas Nações"
    When the edit is stored and rendered
    Then the heading still reads "Labs de Duas Nações"

  Scenario: Allowed markup survives
    Given the reviewer sets a body containing <strong>bold</strong>
    When the edit is stored and rendered
    Then the text renders as bold
    And the literal word "strong" does not appear

  Scenario: Disallowed markup is rejected, not mangled
    Given the reviewer submits a body containing <script>alert(1)</script>
    When the edit is validated
    Then the edit is rejected with an explicit error
    And no partially stripped text is stored

  Scenario: LLM-bound text keeps its protection
    Given topic text containing an injection pattern
    When it is sanitized for an LLM prompt
    Then the injection pattern is removed as before

  Scenario: An omitted required field does not blank the slide
    Given an edit payload missing the heading
    When the edit is validated
    Then it is rejected naming the missing field
```

## Affected Areas

- Backend: `agents/input_sanitizer.py` call sites, slide-edit handlers, localized slide validation
- Frontend: show the rejection reason on an invalid edit
- Database: no
- API: slide edit endpoint — error responses; regenerate pinned artifacts if the contract changes
- Tests: round-trip + injection regression
- Docs: slide-copy markup rules
- Prompts/LLM: no change to prompt content
- Observability: log rejected edits with reason
- Deployment: no

## Dependencies

- Blocks: usable slide editing
- Blocked by: none
- Related: AE-0289 (`sanitize_display_input`), AE-0336 (edits reaching the PDF)

## Implementation Plan

1. Map every call site handling human-authored final copy vs LLM-bound text.
2. Switch the final-copy sites to `sanitize_display_input`.
3. Replace character deletion with allow-list escaping for slide markup.
4. Settle and test the budget/tag-character rule.
5. Add the required-field rejection; document the replace-whole-dict semantics.

## QA Checklist

- [ ] Security reviewed — injection protection must not regress
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (nested tags, unclosed tags, mixed case, accents)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-09-15

Ticket created from the AE-0330 session handoff (defect #11). Confirmed at
`input_sanitizer.py:13-17`; AE-0289 already added the case-preserving variant but
the slide-edit path does not use it.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
