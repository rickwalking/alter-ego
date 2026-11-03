Feature: The copy-budget fit leaves the fast model room to answer (AE-0607)

  In prod (POV QA run, 2026-11-03) the shorten step never landed a rewrite.
  Langfuse showed every fit call spending exactly its 4096-token cap on
  reasoning and returning empty content: 3 x deepseek-v4.1-flash (34.9 s,
  37.8 s, 37.8 s), then the queue's fallback qwen3.8-flash (63.3 s), 173.9 s
  in all, until the step's 180 s deadline fired. The fit prompt v3 lifts the
  cap to the 32000 the drafting and the gate repair already run with.
  Validators, thresholds, the gate repair and every deadline are unchanged.

  Background:
    Given over-budget slide copy

  Scenario: The fit lands a rewrite
    Given the fast model answers with a shorter text
    When the shorten step runs
    Then the field holds the model's text

  Scenario: The fit prompt does not cap a reasoning model at 4096 tokens
    When the fit prompt is rendered
    Then it comes from carousel_copy_budget v3
    And its model block allows 32000 output tokens
    And the v1 prompt still binds 4096 and is otherwise the same text

  Scenario: The provider receives the fit prompt's token budget
    Given the fast model is the OpenCode Go chat model with its 32000 default
    When the fit model is called
    Then the request body asks for max_completion_tokens 32000 and temperature 0.3

  Scenario: An all-reasoning empty answer is a model failure
    Given the fast model spends its budget on reasoning and answers no content
    When the shorten step runs
    Then the slides are unchanged
    And "copy_budget_fit_model_failed" is logged with "EmptyFitAnswerError"
    And the attempts are 1

  Scenario: A model that times out is not asked a second time
    Given the fast model does not answer within the step's deadline
    When the shorten step runs
    Then the slides are unchanged
    And "copy_budget_fit_model_failed" is logged with "TimeoutError"
    And the attempts are 1
