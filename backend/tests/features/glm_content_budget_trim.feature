Feature: Deterministic copy trim for over-budget slide bodies (AE-0286)
  Some chat models (notably GLM 5.2, a reasoning model) over-write slide copy far
  past the per-slide character budgets and restate the heading in the body, which
  blocks content approval. The deterministic presentation repair trims the body
  to budget and strips the repeated heading — meaning-preserving, never nonsense —
  so the content phase can pass validation without a human re-write.

  Scenario: An over-budget body is trimmed to fit
    Given a content slide whose body exceeds the character budget
    When the deterministic repair runs with the presentation policy
    Then the body is shortened to at most the budget
    And it keeps whole sentences where possible (no mid-word cut)

  Scenario: A single oversized sentence falls back to a clean word cut
    Given a body that is one sentence longer than the budget
    When the repair trims it
    Then it cuts on a word boundary and ends with an ellipsis
    And it never exceeds the budget

  Scenario: Dangling markup is balanced after a cut
    Given a body with an open <strong> tag near the cut point
    When the repair trims it
    Then the result has no unbalanced markup tags

  Scenario: A heading repeated in the body is removed
    Given a slide whose body restates the heading text
    When the repair runs
    Then the heading text no longer appears in the body
    And the body still reads as a complete thought

  Scenario: The repaired payload passes the real validator
    Given a content slide that is both over budget and repeats its heading
    When the deterministic repair runs
    Then re-validating the slide reports no body-too-long or heading-repeat violation
