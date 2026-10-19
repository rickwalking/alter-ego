Feature: The content gate repairs only the failing fields (AE-0430)

  Prod carousel 5344b6c6 (news_analysis, hero_lower_third_v4) kept 12 blocking
  violations after two "Feedback para revisão" runs marked "applied": the
  revision never saw the violations, EN lost the PT TL;DR, a "**PT**" scaffold
  marker leaked into the PT body, and items overflowed their character limits.

  Background:
    Given a carousel on the "hero_lower_third_v4" presentation contract
    And a field repair model that answers with the texts it is asked for

  # --- A: targeted repair after validation -------------------------------

  Scenario: An over-limit field is repaired in one round
    Given slide 3 EN "features[0].body" has 121 characters and the limit is 100
    When the content gate runs its repair loop
    Then the model is asked for exactly "3:en:features[0].body"
    And the request carries the current text, the limit of 100 characters and the slide heading
    And the repaired text replaces only that field
    And the content gate report is no longer blocking

  Scenario: Two rounds then stop with the violations shown
    Given the model always answers with text over the limit
    When the content gate runs its repair loop
    Then the model is called exactly 2 times
    And the remaining violations stay in "content_gate_validation"
    And no field is truncated by the repair loop

  Scenario: The repair never touches fields that pass
    Given slide 6 PT "actions[0].body" is over its limit and slide 6 PT "heading" passes
    And the model also answers for "6:pt:heading", which it was not asked for
    When the content gate runs its repair loop
    Then slide 6 PT "heading" keeps its text

  Scenario: A failing model leaves the copy and the report as they were
    Given the field repair model raises an error
    When the content gate runs its repair loop
    Then the localized slides are unchanged
    And the report is still blocking

  Scenario: The regression fixture from prod ends green
    Given the slides 1, 3 and 6 exported from carousel 5344b6c6
    And a fake model that rewrites each requested field within its limit
    When the content gate runs its repair loop
    Then the model is asked only for the failing fields
    And the validator reports no blocking violation

  # --- B: the revision uses the violations ------------------------------

  Scenario: A revision request carries the blocking violations
    Given the content gate holds blocking violations on slides 1, 3 and 6
    And the owner files the note "Fix them"
    When the content phase regenerates with the note
    Then the drafting request carries the owner's note
    And it carries one line per blocking violation with slide, locale, field and limit
    And the repair loop runs after the regeneration

  Scenario: A revision that changes nothing is not recorded as applied
    Given the regeneration returns the same visible copy
    When the content phase finishes the revision
    Then the note moves to the history with status "unchanged"

  Scenario: A revision that changes the copy is recorded as applied
    Given the regeneration returns different visible copy
    When the content phase finishes the revision
    Then the note moves to the history with status "applied"

  # --- C: translation keeps the structured shape ------------------------

  Scenario: EN keeps the TL;DR strip of the intro
    Given the PT intro draft carries a "tldr_strip"
    When the slides are translated to English
    Then the translation request carries the "tldr_strip"
    And the EN intro carries a translated "tldr_strip"
    And no "translation_shape_mismatch" is reported for slide 1

  Scenario: A residual shape mismatch is filled from PT and translated
    Given PT slide 1 is "intro:tldr" and EN slide 1 is "intro:plain"
    When the content gate runs its repair loop
    Then the EN slide gets the missing "tldr_strip" from PT
    And the model is asked to translate "1:en:tldr_strip"
    And no "translation_shape_mismatch" remains

  # --- E: label scaffolding never reaches visible copy ------------------

  Scenario: Bold locale markers are parsed as sections, not copy
    Given a draft whose text is "**PT**" then "**heading:**" and "**body:**" lines, then "**EN**"
    When the localized slides are built
    Then the PT body is the PT body line only
    And the PT body does not contain "**PT**" or "**body:**"
    And the EN heading and body come from the "**EN**" section
