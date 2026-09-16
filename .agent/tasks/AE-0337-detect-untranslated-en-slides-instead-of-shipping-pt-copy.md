# AE-0337 — detect untranslated EN slides instead of shipping PT copy

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

Never publish an EN carousel whose slides are actually Portuguese. Make a missing
or copied translation a **blocking validation failure**, not a silent pass.

## Problem

On carousel `dcaa5fef…` (2026-09-15) the EN translation landed on **2 of 7
slides**. The other 5 carried the **PT text copied verbatim** into the EN
presentation. Nothing caught it: every validation the pipeline runs — budgets,
policy validation, the content gate — is satisfied by text that is present and
within length, regardless of which language it is in. The operator noticed by
reading the slides and hand-authored EN for all 7.

The failure mode is quiet and shipping-grade: an EN artifact renders, exports, and
passes the gates while being mostly untranslated.

## Scope

- A translation-completeness check over the localized slide set: for each slide,
  EN body/heading must not be byte-identical (nor trivially identical after
  whitespace/case normalization) to the PT counterpart.
- A language check for the EN fields strong enough to catch "PT text in the EN
  slot" — a lightweight heuristic (stopword/diacritic ratio) is sufficient and
  avoids a new dependency; escalate to a detector library only if the heuristic
  proves noisy.
- Wire the check into the same validation pass that already enforces policy and
  budgets, so it blocks phase completion.
- Report **which** slides failed and why, so the reviewer can act.

## Non-Goals

- Improving translation *quality* — only detecting absent/copied translations.
- Adding a new LLM call to verify the translation (cost); the heuristic runs offline.
- Supporting locales beyond PT/EN.

## Acceptance Criteria

- [ ] A slide whose EN text equals its PT text (after normalization) fails
      validation and names the slide index.
- [ ] A slide whose EN text is Portuguese by the heuristic fails validation.
- [ ] A correctly translated set passes — the dcaa5fef hand-authored EN is used
      as the positive fixture.
- [ ] The check blocks phase completion; it is not advisory.
- [ ] The heuristic's false-positive behaviour is tested on short strings, proper
      nouns, and shared technical terms (e.g. "AI", "labs").

## Gherkin Scenarios

```gherkin
Feature: Untranslated EN slides are blocked

  Scenario: EN text is a verbatim copy of PT
    Given slide 4's EN body equals its PT body
    When the localized slides are validated
    Then validation fails and names slide 4

  Scenario: EN text is Portuguese
    Given slide 5's EN body is Portuguese prose
    When the localized slides are validated
    Then validation fails and names slide 5

  Scenario: A fully translated deck passes
    Given all 7 slides carry distinct English text
    When the localized slides are validated
    Then validation passes

  Scenario: A shared technical term is not a false positive
    Given slide 1's EN heading and PT heading both contain "AI"
    But the rest of the heading differs
    Then validation passes
```

## Affected Areas

- Backend: localized slide validation (`validate_localized_slides` and callers)
- Frontend: surface the per-slide failure reason
- Database: no
- API: validation report shape may gain a reason code
- Tests: unit + the dcaa5fef fixtures (bad set and hand-authored good set)
- Docs: carousel validation guide
- Prompts/LLM: possibly reinforce the translation instruction in the prompt
- Observability: log which slides failed
- Deployment: no

## Dependencies

- Blocks: trustworthy EN output
- Blocked by: none
- Related: AE-0334, AE-0336

## Implementation Plan

1. Capture the dcaa5fef pre-fix slide set as a negative fixture and the
   hand-authored EN as the positive one.
2. Implement the equality + heuristic language check.
3. Wire into `validate_localized_slides`; make it blocking.
4. Tune against the false-positive cases; document the threshold.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (short strings, proper nouns, numerals-only)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-09-15

Ticket created from the AE-0330 session handoff (defect #10). 5 of 7 slides
shipped PT text in the EN slot with every gate green.

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
