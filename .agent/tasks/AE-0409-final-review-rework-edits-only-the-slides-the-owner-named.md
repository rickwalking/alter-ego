# AE-0409 — Final-review rework edits only the slides the owner named

Status: Intake
Tier: T2
Priority: High
Type: Bug
Area: Backend
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-10-17
Updated: 2026-10-17

## Goal

When the owner sends a carousel back from final review with specific notes, the autopilot changes
only what the notes ask for and keeps every other approved slide exactly as it was.

## Problem

Carousel `be190a0c` (pov_news, autopilot run `f88bc343`), 2026-10-17:

- At 03:44Z the deck reached final review with copy that had passed the content gate (no blockers,
  every persona score ≥ 70).
- At 03:48Z the owner sent it back with two notes: "Title is too big in the first slide, hiding my
  face" and "At the final slide, revoke the 'toda terça e quinta'".
- The rework (`rework_phase=content`) resumed the graph at **content** with the notes as revision
  notes. The content node **regenerated all 9 slides** with the model (03:47:55 → 03:58:15Z).
- The new deck was worse than the approved one:
  - The model returned malformed JSON for slides 4–7 (`carousel_slide_parse_failed`,
    `missing_canonical_keys`, deterministic repair).
  - Slide 6's PT body became "**Português**", and slide 7's starts with "** **".
  - Slide 8 lost its summary points (`summary_points_missing`), and slide 2's EN body was 514
    characters with markup.
  - Persona scores came back as 0.0 (judge failures) on slides 1, 5 and 9.
  - **Slide 1 kept the long title**, so the owner's main request was not applied.
- The run escalated again at 04:04Z (`persona_score_below_threshold`). The orchestrator restored
  the approved copy from the checkpoint history and applied the title change by hand.
- Note 2 was template copy (fixed in AE-0408). The rework had no way to know that a note targets
  something no slide edit can change.

Root shape: a final-review send-back is treated as "regenerate the phase with notes", not as "edit
these slides". Every regeneration risks every approved slide, and spends the model budget.

## Scope

- Turn a final-review send-back into a **targeted edit**:
  1. Map each note to the slide(s) it names ("first slide", "final slide", "slide 3", the CTA, the
     hook) and to a field when possible (title/heading, body, points). One model call to classify
     the notes is acceptable; it must return structured output (slide index, field, instruction).
  2. Rewrite only those slides with the slide fix loop (the AE-0401/AE-0407 path: same validators,
     voice judge and escalation), with the note as the instruction.
  3. Keep every other slide byte-for-byte, along with its persona score.
- Notes that no slide edit can satisfy (template copy such as the CTA template, layout such as
  "title hides my face" when the copy is already short, image changes) are surfaced to the owner on
  Telegram as "needs a template/design change", not silently turned into a regeneration.
- A layout note on the hook ("title too big", "covers my face") is handled as a heading-length
  edit: shorten the heading, keeping the slide's role and the thesis.
- Fall back to the current full-phase regeneration only when the notes ask for it ("rewrite
  everything", "change the angle"), or when no note maps to a slide.
- Record which slides changed in the run's Telegram message to the owner.

## Non-Goals

- Changing how the first content pass is generated.
- Free-form design edits (fonts, colors) from notes.
- The dashboard's manual-fix form (AE-0403) — already targeted.

## Acceptance Criteria

- [ ] A final-review send-back that names slides rewrites only those slides; every other slide's
      `localized_slides` entry, drafts and persona score are unchanged.
- [ ] "Title is too big in the first slide" shortens slide 1's heading (PT and EN) and leaves its
      body and the other slides alone.
- [ ] A note about template copy (for example the CTA template) is reported to the owner as not
      editable by the rework and does not trigger a regeneration.
- [ ] A rewritten slide goes through the slide fix loop (validators, voice judge, AE-0407
      escalation); if it still fails, the run escalates with the slide named, and the approved
      copy of the other slides is kept.
- [ ] "Rewrite everything"-style notes still regenerate the phase (current behavior).
- [ ] Regression test reproducing `be190a0c`: approved deck + the two notes → slide 1 heading
      shortened, slides 2–9 untouched, no model call for slides 2–9.

## Gherkin Scenarios

```gherkin
Feature: Targeted final-review rework

  Scenario: A note that names a slide edits only that slide
    Given a carousel at final review whose 9 slides passed the content gate
    When the owner sends it back with "Title is too big in the first slide, hiding my face"
    Then only slide 1's heading is rewritten, shorter, in PT and EN
    And slides 2 to 9 keep their copy and persona scores
    And the deck returns to final review without a content regeneration

  Scenario: A note about template copy is reported, not regenerated
    Given a carousel at final review
    When the owner's note asks to change text that comes from a template
    Then the owner is told the note needs a template change
    And no slide is regenerated

  Scenario: A targeted rewrite that keeps failing escalates with the slide named
    Given a send-back that names slide 8
    When the rewritten slide 8 still fails the validators after every fix attempt
    Then the run escalates naming slide 8
    And the other slides keep their approved copy

  Scenario: A note asking for a full rewrite regenerates the phase
    Given a carousel at final review
    When the owner sends it back with "rewrite everything with a different angle"
    Then the content phase is regenerated with the note
```

## Delta

### ADDED

- Note → slide/field mapping for final-review send-backs (structured output).
- Targeted rework path on top of the slide fix loop.

### MODIFIED

- Autopilot rework (`modules/autopilot/application` ReworkStep / owner rework) no longer resumes a
  full content regeneration by default.

### REMOVED

- None.

## Affected Areas

- Backend: autopilot rework step, slide fix loop (`application/services/carousel/slide_fix_*`),
  editorial resume.
- Frontend: none.
- Database: none expected.
- API: none.
- Tests: regression from `be190a0c`, Gherkin above.
- Docs: `docs/architecture/grokbot-autopilot.md` rework section.
- Prompts/LLM: a new note-classification prompt (new prompt file, registry-loaded).
- Observability: log which slides a rework changed.
- Deployment: none.

## Dependencies

- Blocks: none.
- Blocked by: AE-0407 (slide fix escalation, judge retries) should land first.
- Related: AE-0401 (model autofix), AE-0405 (content revision notes lifecycle), AE-0408 (CTA template).

## Implementation Plan

1. Architect: read the rework path (ReworkStep, `editorial.resume(action=revise)`) and the slide fix
   loop; decide where the targeted path plugs in and how the checkpoint is patched (the
   owner-autofix `checkpoint_patch` path keeps the content review interrupt intact).
2. Note classifier: structured output, PT/EN, with fakes in tests.
3. Targeted rewrite through the slide fix loop; keep the other slides and scores.
4. Telegram message for non-editable notes and for the list of changed slides.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-17 05:00

Ticket created from the `be190a0c` incident (owner send-back regenerated the deck and escalated).

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
