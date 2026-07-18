Feature: Provider failures on workflow start surface as structured errors
  AE-0319: observed live 2026-07-17 — the GLM endpoint's 429 usage-limit error
  surfaced as a generic 500 with no retry hint. Provider rate limits map to
  HTTP 429 and provider outages to HTTP 503, both logged; non-provider errors
  are unchanged.

  Scenario: Provider rate limit maps to 429
    Given the synthesis LLM raises a provider rate-limit error
    When the editorial workflow is started
    Then the response is 429 with detail "provider_rate_limited"
    And a workflow_start_provider_error is logged with the project id

  Scenario: Provider outage maps to 503
    Given the synthesis LLM raises a provider API error
    When the editorial workflow is started
    Then the response is 503 with detail "provider_unavailable"
    And a workflow_start_provider_error is logged

  Scenario: Non-provider errors are unchanged
    Given the engine raises an unrelated runtime error
    When the editorial workflow is started
    Then the error propagates to the generic handler unchanged
