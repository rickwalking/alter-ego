Feature: Carousel content keeps sentence case, non-empty bodies and reviewer edits (AE-0366)

  Prod carousel 8e350d6e (PT-BR, GLM) shipped a title-only slide, lowercase
  headings and bodies with lowercased proper nouns, and a fully lowercase EN
  translation with mangled <strong> tags, while presentation validation said
  "valid". Reviewer edits made at the content gate never reached the rendered
  slides. Root causes: the content drafter and the EN translator received their
  inputs through the lowercasing, tag-stripping sanitizer; the casing rules were
  warning-only and the bounded repair silently "fixed" only the validated copy;
  nothing validated empty bodies; and edits never re-projected the slide rows.

  Background:
    Given a project stamped with presentation policy hero_lower_third_v3

  Scenario: The drafter and the translator receive correctly cased copy
    Given an outline title "A versão para robótica leva o Argon ao mundo físico"
    When the content drafter builds its prompt
    Then the prompt contains the title with its original casing
    And the EN translation payload keeps casing and <strong> tags

  Scenario: Lowercase headline or body text blocks the content
    Given prod-shaped drafts whose slide 5 heading is "a versão para robótica leva o gemini ao mundo físico"
    And slide 6 is all lowercase in heading, body and actions
    When presentation validation runs
    Then heading_not_sentence_case_pt and body_not_sentence_case_pt are blocking violations
    And the report is blocking

  Scenario: The safe repair capitalizes first letters only
    Given a PT heading "a versão para robótica leva o gemini ao mundo físico"
    And a PT body "à frente, o time testa a api nova. depois publica."
    When the deterministic sentence-case repair runs
    Then the heading becomes "A versão para robótica leva o gemini ao mundo físico"
    And the body becomes "À frente, o time testa a api nova. Depois publica."
    And the unconfigured noun "gemini" is not guessed
    And the repaired fields stay blocking until the slide is regenerated or edited

  Scenario: An empty body on a slide that needs one blocks
    Given a content slide with an empty body and no features
    When presentation validation runs
    Then body_empty is a blocking violation
    And a CTA slide without a body is not flagged

  Scenario: The intentional lowercase allowlist and slide-type exemptions are respected
    Given a heading "iPhone 17 chega ao Brasil"
    Then no casing violation is reported and the repair leaves it unchanged
    And a slide type exempted from a casing rule is neither flagged nor repaired

  Scenario: Lowercase content does not pass content approval
    Given the fail-closed content review of the prod-shaped drafts
    Then the content gate report is blocking
    And approving the content phase is refused with presentation_validation_blocked
    And each blocking slide is regenerated once before the gate

  Scenario: Every quality rubric item has a blocking validator
    Given the quality_rubric of hero_lower_third_v3
    Then every rule code it names fires on a seeded violation and blocks
    And the content and translation prompts render the rubric with a self-check step

  Scenario: A reviewer edit reaches the persisted slides and the render
    Given persisted slide rows for the prod-shaped drafts
    When the reviewer edits slide 5 at the content gate and resumes
    Then the slide row heading, body, features and translation_en follow the edit
    And the image path, image prompt and long-form notes are unchanged
    And the rendered HTML shows the edited copy
    And the draft title follows the edited presentation_pt heading
