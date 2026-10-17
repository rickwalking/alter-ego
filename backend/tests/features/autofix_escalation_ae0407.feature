Feature: Content autofix escalates to a stronger model, and the bugs that stalled be190a0c (AE-0407)
  After 3 failed fast-model attempts on a slide, the autopilot slide fix
  tries the stronger reasoning model up to 2 more times before it escalates
  to the owner. Persona scores are read on one 0-100 scale, a failed judge
  call is never a verdict, a correct model rewrite clears a stale casing
  marker, and @handles and URLs keep their case.

  # Item 1: escalation to the reasoning model

  Scenario: Fixed on attempt 2 by the fast model
    Given slide 3's PT body has an emoji
    And the fast model answers with an emoji once, then clean copy
    When the slide fix runs
    Then the slide is fixed after 2 attempts
    And both attempts are logged with model role "fast"
    And the reasoning model is never called

  Scenario: Fixed on attempt 4 by the reasoning model, and the gate approves
    Given slide 3's PT body has an emoji
    And the fast model always answers with an emoji
    And the reasoning model answers clean copy
    When the runner ticks
    Then attempts 1 to 3 are logged with model role "fast" and outcome "still_failing"
    And attempt 4 is logged with model role "reasoning" and outcome "fixed"
    And the gate is approved

  Scenario: Still failing after 5 attempts escalates with every attempt counted
    Given slide 3's PT body has an emoji
    And both models always answer with an emoji
    When the runner ticks
    Then the run is escalated with reason "content_quality"
    And the escalation lists "slide 3" and "(5 fix attempts)"
    And attempts 4 and 5 are logged with model role "reasoning"

  Scenario: Escalation attempts 0 escalates after 3 attempts
    Given AUTOPILOT_AUTOFIX_ESCALATION_ATTEMPTS is 0
    And slide 3's PT body has an emoji
    And the fast model always answers with an emoji
    When the runner ticks
    Then the escalation lists "(3 fix attempts)"
    And the reasoning model is never built

  Scenario: A reasoning-model error counts as an attempt
    Given the fast model always answers with an emoji
    And the reasoning model fails once, then answers clean copy
    When the slide fix runs
    Then attempt 4 is "model_error" and attempt 5 is "fixed"

  # Item 2: persona score scale on every read

  Scenario Outline: A stored overall is read on the 0-100 scale
    Given slide 1's stored persona overall is <stored>
    When the slide fix targets, the autopilot snapshot and the approve check read it
    Then each reads <read>

    Examples:
      | stored | read     |
      | 8.7    | 87       |
      | 75     | 75       |
      | 0.0    | unscored |
      | "bad"  | unscored |

  Scenario: An unscored slide is not a low voice score
    Given slide 1's stored persona overall is 0.0 and the others are 80
    When the content gate is read
    Then the lowest persona score is 80
    And slide 1 is not a voice_score_low target
    And content approval is allowed

  Scenario: The judge's overall on 0-10 is scaled even when a sub-score is on 0-100
    Given the judge answers tone_match 78 and overall 7.8
    When the answer is parsed
    Then overall is 78

  # Item 3: judge failures are not verdicts

  Scenario: A judge call that parses to 0.0 is retried once
    Given the judge answers overall 0.0, then overall 82
    When a rewritten slide is scored
    Then the slide's score is 82

  Scenario: A judge that fails twice leaves the slide unscored
    Given slide 2's previous score is 50
    And the judge raises, then answers without an overall
    When the rewritten slide 2 is scored
    Then slide 2 keeps its previous score 50
    And slide 2 is not marked voice_score_low by the rewrite
    And "persona_judge_failed" is logged
    And no 0.0 score is written

  Scenario: A judge timeout is a failure, not a verdict
    Given the judge never answers within the timeout twice
    When a slide is scored
    Then the slide is unscored

  Scenario: The content phase omits an unscored slide
    Given the judge fails twice on slide 2's draft
    When the content phase scores the slides
    Then persona_scores has no "slide_2" entry
    And every other slide has its score

  # Item 4: the model fix can clear casing markers

  Scenario: Slide 8: casing markers only, rewritten correctly, slide fixed
    Given slide 8's only blockers are casing_repairs markers on its PT heading
    And the model rewrites the PT heading starting with an uppercase letter
    When the slide fix runs
    Then the PT heading marker is dropped
    And the slide is fixed

  Scenario: A rewrite that still starts lowercase keeps the marker
    Given slide 8 has a casing_repairs marker on its PT heading
    And the model rewrites the PT heading starting lowercase
    Then the marker is kept

  Scenario: A field the model did not answer keeps its marker
    Given slide 8 has casing_repairs markers on its PT heading and EN heading
    And the model answers only the PT heading
    Then the EN heading marker is kept

  # Item 5: handles and URLs keep their case

  Scenario: A sentence starting with an @handle is left alone
    Given the PT body "@taylorhbuilds viu o modelo falhar. depois testou."
    When the sentence-case check and the repair run
    Then "@taylorhbuilds" keeps its case
    And the second sentence is flagged and capitalized to "Depois"

  Scenario: A sentence starting with a URL is left alone
    Given the PT heading "https://example.com mostra os números"
    Then it is not flagged and not rewritten

  Scenario: A plain lowercase start is still repaired
    Given the PT heading "taylor viu o modelo falhar"
    Then it is flagged and capitalized to "Taylor viu o modelo falhar"
