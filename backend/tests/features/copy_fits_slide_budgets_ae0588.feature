Feature: Generated slide copy fits the slide length budgets (AE-0588)

  A fresh POV carousel stopped at the content gate because the generated copy
  was 25-40% over the slide budgets on several slides at once (prod QA run,
  2026-11-01). Pedro's decision (2026-11-01): the prompts state each field's
  budget from the same contract values the validator uses, and an automatic
  shorten step rewrites every over-budget field before the presentation
  validation. Validators and thresholds stay exactly as they are.

  Background:
    Given a carousel on a presentation contract with copy budgets
    And a fast model double that answers with the texts it is given

  # --- A: budgets in the prompts --------------------------------------------

  Scenario: The drafting instruction states this slide's field limits from the contract
    Given content slide 3 of a "pov_hook_v1" deck
    When the content instruction is built for slide 3
    Then it lists the heading and body limits the validator enforces on a content slide
    And it lists the feature item title and body limits

  Scenario: A changed contract value changes the prompt budget
    Given a contract whose content body budget is changed to 123 characters
    When the slide limits are rendered for a content slide
    Then the body limit in the prompt is 123 characters

  Scenario: The hook slide limit carries the word limit the validator applies
    Given slide 1 of a "pov_hook_v1" deck, whose contract role is "hook"
    When the slide limits are rendered for the hook slide
    Then the Portuguese heading limit includes at most 10 words
    And the English heading limit and a slide without the hook role carry no word limit

  Scenario: The translation request carries each slide's field limits
    Given PT drafts of a summary slide with summary points
    When the EN translation prompt is built
    Then every slide in the request carries its heading, body and item limits
    And the prompt tells the model every English field must fit its limit

  Scenario: The POV content prompts carry no hardcoded character numbers
    When the v3 POV and POV news content prompts are rendered for every role
    Then no character count appears outside the contract limits block

  # --- B: shorten step before validation ------------------------------------

  Scenario: Over-budget fields are rewritten within budget and pass
    Given slide 3 PT body is 260 characters and the limit is 200
    When the shorten step runs
    Then the model is asked for exactly "3:pt:body"
    And the rewritten body replaces the field
    And the slide has no length violation

  Scenario: Fields within budget are never sent to the model
    Given slide 3 PT body is over budget and slide 3 PT heading is within budget
    When the shorten step runs
    Then the request does not contain "3:pt:heading"

  Scenario: Portuguese and English fields are both handled
    Given slide 3 PT body and EN body are both over budget
    When the shorten step runs
    Then the model is asked for "3:pt:body" and "3:en:body"
    And the EN target carries the Portuguese source

  Scenario: Nested summary point bodies are shortened
    Given slide 9 PT "summary_points[1].body" is 123 characters and the limit is 90
    When the shorten step runs
    Then the model is asked for "9:pt:summary_points[1].body"
    And only that item body changes

  Scenario: The attempts are bounded
    Given the model always answers with text still over the limit
    When the shorten step runs
    Then the model is called exactly 2 times

  Scenario: A rewrite that is still too long is kept only when it is shorter
    Given the model answers with a shorter text that is still over the limit
    When the shorten step runs
    Then the field holds the shortest answer
    And the length violation is left to the normal validation

  Scenario: A rewrite that breaks emphasis is rejected
    Given the model answers with a body that has an unbalanced "**"
    When the shorten step runs
    Then the body keeps its original text

  Scenario: A rewrite that drops the final punctuation is rejected
    Given the model answers with a content body that ends on a comma
    When the shorten step runs
    Then the body keeps its original text

  Scenario: A rewrite with a forbidden persona phrase is rejected
    Given the persona forbids "game changer"
    And the model answers with a body containing "game changer"
    When the shorten step runs
    Then the body keeps its original text

  Scenario: A failing model leaves the copy as it was
    Given the model raises an error
    When the shorten step runs
    Then the slides are unchanged

  Scenario: A model that times out leaves the copy as it was
    Given the model does not answer within the step timeout
    When the shorten step runs
    Then the slides are unchanged

  Scenario: A Portuguese field answered in English is rejected
    Given the model answers a PT body with an English sentence
    When the shorten step runs
    Then the PT body keeps its original text

  Scenario: The owner's hook heading is never rewritten
    Given the hook slide's PT heading is over budget
    And the owner picked a hook, or the heading is the approved outline title
    When the shorten step runs
    Then "1:pt:heading" is not sent to the model and is left to block
    And the EN hook heading may still be shortened

  Scenario: Shortened copy is written back to the drafts and EN translations
    Given slide 3 PT and EN bodies are over budget in the drafts
    When the draft shorten step runs
    Then the draft of slide 3 carries the shortened PT and EN bodies
    And the EN translation of slide 3 carries the shortened body

  Scenario: The QA evidence shapes end with no length violation
    Given the drafts reproduce the 2026-11-01 QA lengths
    When the shorten step runs with a model that answers within the limits
    Then no heading_too_long, body_too_long or copy_too_many_lines violation remains

  # --- C: content phase ordering --------------------------------------------

  Scenario: The shorten step runs before the presentation validation
    Given the content phase with an over-budget slide and a fake fit model
    When the content artifacts are ensured
    Then the fit model is called before the presentation review is built
    And the presentation review validates the shortened copy

  Scenario: Persona voice scores are recomputed for the changed slides
    Given the content phase with a persona and an over-budget slide
    When the content artifacts are ensured
    Then the changed slide is scored again and unchanged slides keep their scores

  Scenario: A shortening that drops the voice under the floor is undone
    Given a slide whose voice score was at least 70 before the shortening
    And its new voice score is below 70
    When the shorten step finishes
    Then the slide's draft, EN translation and score go back to their previous values
    And no extra model call is made

  Scenario: A parked content review replay never calls the fit model
    Given the content review is parked after the shorten step ran once
    When the owner approves and the content node replays
    Then the fit model is not called again
