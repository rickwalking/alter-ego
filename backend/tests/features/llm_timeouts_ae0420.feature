Feature: LLM call budgets cover a slow OpenCode Go endpoint (AE-0420)

  On 2026-10-18 the Go endpoint answered a ~4,000-character draft in 13 to 134 seconds.
  A 120-second fast budget timed content drafting out and failed two carousels.

  Scenario: The fast role waits long enough for a slow long draft
    Given the fast role
    Then one attempt may take at least 300 seconds

  Scenario: The reasoning role keeps a larger budget than the fast role
    Given the reasoning role
    Then one attempt may take at least 360 seconds
    And that is more than the fast role's budget

  Scenario: The fallback budget is no shorter than the fast role's
    Given the fallback model
    Then one attempt may take at least 300 seconds
