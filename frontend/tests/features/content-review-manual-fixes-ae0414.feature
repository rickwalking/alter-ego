Feature: Content review shows, edits and submits every slide honestly (AE-0414)
  As a carousel owner at the content gate
  I want every slide and every flagged field to be reviewable and editable
  So that I can fix the blockers by hand without losing or corrupting copy

  # QA report 2026-10-16: B10, B11, B04, B09, B02 (frontend part), B29, B24 (violation messages)
  # Tests:
  #   src/modules/editorial/workspace/lib/presentation-slide-resolution.test.ts
  #   src/modules/editorial/workspace/lib/presentation-copy-budgets.test.ts
  #   src/modules/editorial/workspace/lib/presentation-emphasis.test.ts
  #   src/app/dashboard/create/workspace/phase-review/content-phase-review.manual-fixes.test.tsx
  #   src/modules/editorial/workspace/components/auto-repair-button.test.tsx
  #   src/modules/editorial/workspace/hooks/use-editorial-workflow.manual-fixes.test.ts

  # B10
  Scenario: Every slide renders even when some drafts lack presentations
    Given a deck of 7 slides in "localized_slides"
    And only slides 1, 2, 6 and 7 carry "presentation_pt" and "presentation_en" in their drafts
    When the owner opens the content review
    Then slides 1 to 7 are all rendered as cards

  Scenario: The validated localized copy wins over the draft copy of the same slide
    Given slide 2 has a draft presentation and a different localized copy
    When the owner opens the content review
    Then slide 2 shows the localized copy (the copy the violations point at)

  Scenario: A malformed localized slide falls back to its draft presentation
    Given slide 1's localized PT body is raw JSON and its draft has a structured presentation
    When the owner opens the content review
    Then slide 1 shows the draft presentation

  Scenario: A "Slide N" link focuses a real slide card
    Given slide 3 carries a blocking violation without an editable field
    When the owner clicks the "Slide 3" link
    Then the slide 3 card receives focus

  # B11
  Scenario: A flagged summary point is editable in both locales
    Given slide 2's EN "summary_points[0].body" carries "body_too_long"
    When the owner opens the editable content review
    Then the PT and EN columns show a title and a body field for each summary point
    And the EN item 1 body field is flagged with the translated message
    When the owner edits the EN item 1 body
    Then its error clears and the manual fixes include the edited item

  Scenario: CTA structured fields show their values and are editable
    Given the CTA slide has "creator_name" "Pedro Marins" and an empty "creator_website"
    When the owner opens the editable content review
    Then a "Creator name" field holds "Pedro Marins"
    And the read-only review shows "(empty)" for the empty website

  # B04
  Scenario: Manual fixes send only the changed slides, verbatim
    Given slide 1's PT body is 300 characters (over its 220 budget)
    And slide 2 is untouched
    When the owner edits slide 1's EN heading and submits the manual fixes
    Then the payload carries slide 1 only
    And slide 1's PT body is the full 300 characters, never cut

  # B09
  Scenario: Auto-fix that cannot fix anything says so
    Given "POST /repair" returns status "noop" with remaining codes and 38 blocking violations
    When the owner clicks "Fix issues automatically"
    Then the UI says it could not fix 38 issues automatically
    And it does not claim that nothing was needed
    And it does not re-read the workflow state

  Scenario: Auto-fix with nothing left says there was nothing to fix
    Given "POST /repair" returns status "noop" with no violations
    When the owner clicks "Fix issues automatically"
    Then the UI says there was nothing to fix automatically

  # B02 (frontend part)
  Scenario: A rejected manual fix shows a translated message and no page error
    Given "POST /workflow/resume" answers 422 "edited_localized_slides_phase_not_allowed"
    When the owner submits manual fixes
    Then the workflow error shows the translated message, not the raw code
    And the submission resolves without an uncaught rejection

  # B29
  Scenario: A live counter warns when copy is over budget on a v4 deck
    Given the deck uses policy "hero_lower_third_v4"
    When the owner types a 5000 character body on a content slide
    Then the counter under the body shows "5000/220 characters" as an alert

  Scenario: Each locale states its emphasis convention
    When the owner opens the editable content review
    Then the PT column hints "**…**" and the EN column hints "<strong>…</strong>"

  Scenario: Copy using the other locale's emphasis can be converted
    Given the PT body contains "<strong>limites claros</strong>"
    When the owner clicks "Convert emphasis"
    Then the PT body contains "**limites claros**"

  # B24 (violation messages)
  Scenario: Violation messages are translated
    Given a "slide_parse_failed" violation with an English backend message
    When the owner opens the content review
    Then the violation line shows the translated message and the field label
