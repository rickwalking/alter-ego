# AE-0309 — Carousel content drafter must fail closed on scaffold parse failure

Status: Ready
Tier: T2
Priority: High
Type: Bugfix
Area: backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-07-10
Updated: 2026-07-10

## Goal

A per-slide drafting parse failure can never silently store the raw drafting
scaffold as visible slide copy. The content phase validates its own output at
write time, repairs deterministically when possible, retries once when not,
and — as a last resort — surfaces a blocking, user-visible validation error
**at the content step** (not phases later at design).

## Problem

Prod incident (project `38affb3e-c219-4c56-9838-9cae7094f767`, 2026-07-07):
a content-phase regeneration ("fix slide 6") corrupted slide 4 — the PT
extraction from `draft_text` failed and the pipeline stored the **entire raw
drafting scaffold** (`## PT / **Heading:** / **Body:** / **Features:** /
## EN / ## Image Prompt`, 1147 chars) as `presentation_pt.body`, with the
`content_kind`/`features` keys missing. Nothing failed at write time. The
corruption was only caught later by the design-phase presentation validator
(`drafting_scaffold_present`, `heading_repeated_in_body`, `body_too_long`),
by which point the workflow was unrecoverable through the UI (see AE-0310)
and required manual checkpoint-blob surgery in prod.

Root gap: `localized_slide_builder._build_locale_payload` falls back to the
whole raw draft when locale extraction fails, and the content phase never
re-validates what it just built.

## Scope

- Backend: in the content-phase artifact path, validate every built
  `localized_slides` locale payload with the existing
  `validate_slide_payload` (policy-aware) immediately after building.
- On parse failure of a locale payload:
  1. Run the existing deterministic repair
     (`presentation_review_repair.attempt_locale_repair` — scaffold strip,
     body trim, shape normalization) and re-validate.
  2. If still invalid, retry the LLM draft for that slide once.
  3. If still invalid, mark the content phase artifact with a blocking
     per-slide validation report so the interrupt payload carries the
     violations to the content review step.
- A locale payload must always carry the canonical shape
  (`slide_type`, `heading`, `body`, `content_kind`, `features`) — a partial
  dict is itself a parse failure.
- Frontend: the content step renders the per-slide violations from the
  content-phase interrupt payload (same visual treatment as the design-step
  violations today) so the reviewer sees exactly which slide failed and why
  **before** approving.
- Structured log event (`carousel_slide_parse_failed`) with project_id,
  slide_index, locale, and repair outcome for observability.

## Non-Goals

- No new validation rules (casing is AE-0312).
- No repair endpoint / UI button (AE-0311).
- No changes to the design-phase flow (AE-0310).
- No prompt changes to reduce scaffold emission (separate tuning concern).

## Acceptance Criteria

- [ ] A draft whose PT extraction fails never persists scaffold text: either
      the deterministic repair fixes it, the single retry fixes it, or the
      content phase interrupts with a blocking per-slide validation report.
- [ ] `localized_slides` payloads always have the canonical key set; a
      missing `content_kind`/`features` key is treated as a parse failure.
- [ ] The content-step UI displays per-slide violations from the interrupt
      payload (slide number, rule code, message) in both locales.
- [ ] `carousel_slide_parse_failed` is logged with repair outcome.
- [ ] Regression test reproducing the AE-incident payload (full scaffold as
      body) proves the write path rejects/repairs it (rule-fires test).
- [ ] Existing green-path drafting behavior unchanged (snapshot tests pass).
- [ ] The fail-closed chain keys strictly on the validation report's
      `blocking` flag — violations in a report with `blocking=False` (e.g.
      future warning-severity rules, AE-0312) never consume the LLM retry
      and never interrupt with a blocking report.

## Gherkin Scenarios

```gherkin
Feature: Content drafting fails closed on parse failure

  Scenario: Deterministic repair rescues a scaffold-contaminated slide
    Given a slide draft whose PT extraction returns the full drafting scaffold
    When the content phase builds localized slides
    Then the deterministic repair strips the scaffold and trims the body
    And the stored presentation_pt body contains no scaffold labels
    And the payload has the canonical key set

  Scenario: Unrepairable slide surfaces at the content review step
    Given a slide draft that fails extraction, repair, and one retry
    When the content phase interrupts for human review
    Then the interrupt payload carries a blocking violation for that slide
    And the content step UI shows the slide number and violation messages

  Scenario: The single LLM retry rescues an unrepaired slide
    Given a slide draft that fails extraction and deterministic repair
    And the retried LLM draft parses cleanly
    When the content phase builds localized slides
    Then the retried draft's payload is stored with the canonical keys
    And no blocking violation is reported for that slide
    # Test harness: injectable fail-then-succeed draft double (LLM mock)

  Scenario: Clean drafts are unaffected
    Given seven slide drafts that parse cleanly
    When the content phase builds localized slides
    Then no repair or retry runs and the artifact matches today's snapshot
```

## Delta

### ADDED

- Post-build validation + bounded repair + single retry in the content-phase
  artifact runner.
- `carousel_slide_parse_failed` log event.
- Content-step violation rendering in the create flow (frontend).

### MODIFIED

- `localized_slide_builder` fallback path (no raw-draft fallback into `body`).
- Content-phase interrupt payload schema (optional per-slide violations).

### REMOVED

- Silent whole-draft fallback when locale extraction fails.

## Affected Areas

- Backend: `application/services/carousel/localized_slide_builder.py`,
  `presentation_review_repair.py`, content-phase artifact runner
- Frontend: content step of `dashboard/create/[id]` (violation panel)
- Database: none
- API: content interrupt payload (additive field)
- Tests: unit + `.feature` (behavior change), rule-fires regression
- Docs: qa-checkpoints reference if a new gate is added
- Prompts/LLM: none
- Observability: new structured log event

## Dependencies

- Blocks: AE-0311 (repair endpoint reuses the same deterministic repair)
- Blocked by: none
- Related: AE-0310, AE-0286 (deterministic trim), AE-0290

## Implementation Plan

1. Reproduce the incident payload as a unit fixture (raw scaffold body).
2. Harden `_build_locale_payload`: extraction failure returns a typed
   failure, never the raw draft.
3. Wire validate → repair → retry → blocking-report chain in the content
   artifact runner.
4. Extend interrupt payload + frontend content step to render violations.
5. Add rule-fires regression + snapshot tests; run full gates.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (EN-only failure, both-locale failure, retry success)
- [ ] Orphan/unfinished code checked
- [ ] Cross-ticket invariant note: the "warnings don't trigger
      fail-closed" behavior is exercised by AE-0312's integration test;
      if AE-0312 is deferred, add a mock-severity test here so the
      `blocking=False` branch has a live exerciser (cold-critic r6)

## Progress Log

### 2026-07-10

Ticket created from prod incident analysis (session: carousel validation
debugging, projects 38affb3e / 66014ba3).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

### 2026-07-10 — Cold-critic cross-ticket coupling resolved (AE-0312)

External GLM 5.2 review flagged that once AE-0312 introduces
warning-severity casing rules, this ticket's fail-closed chain must not
retry/interrupt on them. Resolution: the chain keys strictly on the
report's `blocking` flag (AC added). Ships safely in either order: before
AE-0312 no warning rules exist; after, the severity-aware blocking decision
keeps warnings out of the chain.

## Blockers

None.

## Final Summary

Pending.
