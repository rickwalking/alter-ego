Feature: The copy-budget fit reaches the fallback model before its deadline (AE-0607)

  In prod (POV QA run, 2026-11-03) the shorten step timed out twice after
  exactly 180 s and never landed a rewrite. The step's 180 s deadline fired
  before the fast role's own deadline (300 s per call, 3 tries) let the queue
  move to its fallback model, so the fallback never ran. The 180 s budget is
  kept and split: the primary model gets a window, the role's fallback model
  gets the rest. Validators, thresholds and the gate repair are unchanged.

  Background:
    Given over-budget slide copy
    And a fit model with the fast role's fallback model

  Scenario: The fit lands a rewrite
    Given the primary model answers in time with a shorter text
    When the shorten step runs
    Then the field holds the primary model's text
    And the fallback model is not called

  Scenario: The primary model is slow and the fallback answers
    Given the primary model does not answer within its window
    And the fallback model answers with a shorter text
    When the shorten step runs
    Then the field holds the fallback model's text
    And the fallback use is logged with the reason "TimeoutError"
    And the whole attempt stays inside the step's 180 s budget

  Scenario: The fallback answer keeps the attempts going
    Given the primary model does not answer within its window
    And the fallback model's first answer is shorter but still over budget
    When the shorten step runs
    Then a second attempt is made
    And the attempts are 2

  Scenario: Both models fail and the copy is kept and logged
    Given the primary model does not answer within its window
    And the fallback model does not answer before the step's deadline
    When the shorten step runs
    Then the slides are unchanged
    And "copy_budget_fit_model_failed" is logged with "TimeoutError"
    And the attempts are 1

  Scenario: An unparseable primary answer goes to the fallback
    Given the primary model answers text that is not the fixes JSON
    And the fallback model answers with a shorter text
    When the fit model is called
    Then the answer is the fallback model's text

  Scenario: Any other primary failure is not repeated on the fallback
    Given the primary model raises an error after trying its whole queue
    When the fit model is called
    Then the error is raised
    And the fallback model is not called

  Scenario: Without a fallback the primary keeps the whole budget
    Given a fit model without a fallback model
    And the primary model answers after its window but inside the step's budget
    When the fit model is called
    Then the answer is the primary model's text

  Scenario: The fit prompt does not cap a reasoning model at 4096 tokens
    When the fit prompt is rendered
    Then it comes from carousel_copy_budget v3
    And its model block allows 32000 output tokens
    And the v1 prompt still binds 4096
