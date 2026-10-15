Feature: Per-task LLM model routing, GLM fallback and parallel slide drafting (AE-0391)
  GLM-5.3 is a reasoning model: a carousel content phase made ~15 sequential
  calls of 3-10 min each (60+ min). Carousel LLM calls are now routed per task
  to DeepSeek models on the same OpenCode Go endpoint (reasoning vs fast), fall
  back to GLM-5.3 when the primary call fails, and slides are drafted in
  parallel behind a bounded semaphore.

  Background:
    Given llm_provider is "glm" and a GLM api key is set

  # --- Routing ----------------------------------------------------------------

  Scenario: the reasoning role uses the reasoning model
    Given LLM_MODEL_REASONING is "deepseek-v4-pro"
    When the chat model is built for the "reasoning" role
    Then the primary model is "deepseek-v4-pro" on the OpenCode Go endpoint
    And its per-call timeout is 240 seconds
    And its fallback model is LLM_MODEL_FALLBACK ("glm-5.3")

  Scenario: the fast role uses the fast model
    Given LLM_MODEL_FAST is "deepseek-v4.1-flash"
    When the chat model is built for the "fast" role
    Then the primary model is "deepseek-v4.1-flash" on the OpenCode Go endpoint
    And its per-call timeout is 120 seconds

  Scenario: model ids come from settings, not code
    Given LLM_MODEL_FAST is overridden to "glm-5.3-flash"
    When the chat model is built for the "fast" role
    Then the primary model is "glm-5.3-flash"

  Scenario: role routing keeps the Anthropic provider semantics
    Given llm_provider is "anthropic"
    When the chat model is built for any role
    Then it is the configured ChatAnthropic model, unwrapped

  Scenario: role routing without a GLM key degrades to Anthropic
    Given llm_provider is "glm" and the GLM api key is empty
    When the chat model is built for any role
    Then it is the configured ChatAnthropic model

  Scenario: the carousel pipeline uses the right role per task
    When the editorial workflow is wired with reasoning and fast models
    Then research synthesis and the outline use the reasoning model
    And slide drafting, persona scoring, translation, caption and the owner
      autofix re-translate use the fast model

  # --- Fallback ---------------------------------------------------------------

  Scenario Outline: the fallback model answers when the primary call fails
    Given the primary model fails with <failure>
    When a carousel LLM call is made
    Then the fallback model answers the call
    And a structured "llm_fallback_used" warning is logged with the reason
    And the fallback generation is tagged "fallback:true" in Langfuse

    Examples:
      | failure                    |
      | a 5xx server error         |
      | a 429 rate limit           |
      | a timeout                  |
      | empty content              |

  Scenario: an auth failure is not masked by the fallback
    Given the primary model fails with a 401 authentication error
    When a carousel LLM call is made
    Then the error is raised and the fallback is not called

  Scenario: bad JSON after the existing retry falls back
    Given the primary model keeps returning unparseable JSON
    When a JSON agent call exhausts the re-roll and repair retry
    Then the same call is retried once on the fallback model
    And the parsed fallback answer is returned

  Scenario: no fallback configured keeps the existing error contract
    Given the model has no fallback
    When a JSON agent call exhausts the retry
    Then ValueError(ERR_INVALID_JSON) is raised as before

  Scenario: every generation records its role and model
    When a routed call runs
    Then its run carries the tags "role:<role>" and "model:<model id>"

  # --- Parallel slide drafting --------------------------------------------------

  Scenario: slides are drafted concurrently and kept in slide order
    Given a 7-slide outline
    When the content phase drafts the slides
    Then the drafts are returned in outline order
    And at most CONTENT_DRAFT_CONCURRENCY (default 4) drafts are in flight

  Scenario: a slide draft only sees sibling OUTLINE context
    When slides are drafted in parallel
    Then each draft receives the other slides' outline titles and key points
    And no draft depends on another slide's freshly generated draft

  Scenario: one failing slide does not redo the others
    Given one slide's primary model returns bad JSON
    When the content phase drafts the slides
    Then only that slide is retried, then sent to the fallback model
    And the other slides are drafted once

  Scenario: a slide that still fails fails the phase after siblings settle
    Given one slide fails even on the fallback
    When the content phase drafts the slides
    Then no sibling draft is left running
    And the phase fails with the slide's error
