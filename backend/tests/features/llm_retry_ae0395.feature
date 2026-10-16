Feature: LLM calls retry the same model before falling back (AE-0395)
  Prod 2026-10-16: one bad answer from the fast model failed a whole content
  phase, and the GLM-5.3 fallback returned empty content after ~8.5 minutes,
  four times in a row. Every model now gets 5 attempts, and each role falls
  back to a fast Qwen model instead of GLM.

  Scenario: A transient failure is retried on the same model
    Given the fast model fails twice and then answers
    When a carousel call is made
    Then the answer comes from the fast model on its third attempt
    And the fallback model is never called

  Scenario: The fallback is used only after 5 failed attempts
    Given the fast model fails on every attempt
    When a carousel call is made
    Then the fast model is tried 5 times
    And the fallback model answers

  Scenario: The fallback also gets 5 attempts
    Given the fast model and its fallback fail on every attempt
    When a carousel call is made
    Then each model is tried 5 times
    And the last error is raised

  Scenario: Auth errors are not retried
    Given the fast model answers 401
    When a carousel call is made
    Then the error is raised after a single attempt

  Scenario: Backoff grows and is capped
    When attempts 1 to 5 fail
    Then the waits are 2, 4, 8, 15 and 15 seconds

  Scenario: Bad JSON is retried on the same model before the fallback
    Given the fast model answers prose instead of JSON
    When a JSON carousel call is made
    Then the fast model gets 5 attempts before the fallback is asked

  Scenario: Each role falls back to a fast non-GLM model
    When the role models are built with the default settings
    Then the fast role falls back to qwen3.8-flash
    And the reasoning role falls back to qwen3.8-max
