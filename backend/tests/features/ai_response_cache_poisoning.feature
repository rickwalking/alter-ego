Feature: Carousel agents survive a bad LLM response (AE-0330)
  The carousel agents share a process-wide TTL cache of raw LLM responses. When
  a response that cannot be parsed is written into it, every retry replays the
  same failure for the whole TTL window without ever calling the model again —
  so the phase fails in milliseconds and the user cannot recover by retrying.

  Observed in production 2026-09-14: GLM 5.2 spent 31999 of its 32000 tokens
  reasoning and returned empty content. The empty string was cached, and the
  next approve failed instantly with no LLM call and a blank error message.

  Background:
    Given the outline and content-draft agents share the AI response cache

  Scenario: an empty model response is not cached
    Given the model returns empty content
    When the agent parses it and fails
    Then nothing is written to the cache
    And the next attempt calls the model again instead of replaying the failure

  Scenario: a poisoned entry from an older deploy is evicted on read
    Given the cache already holds a response that no longer parses
    When the agent reads it
    Then the entry is evicted and a warning is logged
    And the agent falls through to a fresh model call

  Scenario: a response that parses is still cached
    Given the model returns well-formed content
    When the agent parses it successfully
    Then it is written to the cache
    And a repeated request is served from the cache without calling the model

  Scenario: an empty response is re-rolled instead of failing the phase
    Given the model returns empty content
    When the agent detects there is nothing to parse
    Then it re-rolls the original call once
    And a good second sample completes the phase normally

  Scenario: the re-roll is bounded
    Given the model returns empty content twice in a row
    When the agent has exhausted its re-roll
    Then it raises the invalid-JSON error
    And nothing unparseable is written to the cache

  Scenario: malformed but present output is repaired
    Given the model returns text that is not valid JSON
    When the agent hands it back with the JSON repair prompt
    Then the repaired response is parsed and the phase completes
