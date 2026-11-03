Feature: A failed carousel phase records why it failed

  When a background resume fails, the carousel row, the workflow_failed event and
  the generation run say why: the error class and a short safe code, never the
  raw exception message, a prompt or user content. The EN slide translation gets
  the same JSON retry and fallback as every other JSON-producing LLM call.

  Scenario: A malformed EN translation is retried on the fallback model
    Given the primary model answers the EN translation with malformed JSON every time
    And the fallback model answers with valid translation JSON
    When the content phase translates the slides to English
    Then the fallback model is called
    And the slides get the fallback model's English translation

  Scenario: An EN translation that never parses still fails with its own code
    Given every model answers the EN translation with malformed JSON
    When the content phase translates the slides to English
    Then the translation raises "en_translation_parse_failed"

  Scenario: A ValueError during a resume is stored on the carousel row
    Given a carousel resuming from its outline gate
    When the resume raises ValueError "en_translation_parse_failed"
    Then the carousel phase status is "failed"
    And the carousel error message is "ValueError: en_translation_parse_failed"
    And the workflow_failed event has error type "ValueError" and reason "en_translation_parse_failed"

  Scenario: A free-text failure message never reaches the row or the event
    Given a carousel resuming from its outline gate
    When the resume raises ValueError "topic about Pedro's secret plan"
    Then the carousel error message is "ValueError: unclassified"
    And the workflow_failed event reason is "unclassified"

  Scenario: A sentence-style error constant is mapped to its code
    Given a carousel resuming from its outline gate
    When the resume raises ValueError "Invalid JSON response from LLM"
    Then the carousel error message is "ValueError: invalid_json"

  Scenario: An unexpected exception during a resume is stored on the row too
    Given a carousel resuming from its outline gate
    When the resume raises RuntimeError "boom"
    Then the carousel error message is "RuntimeError: unclassified"

  Scenario: A generation run whose workflow failed is not marked succeeded
    Given a queued generation run whose resume fails with "ValueError: en_translation_parse_failed"
    When the job handler finishes the run
    Then the run status is "dead_letter"
    And the run last error code is "workflow_failed"
    And the run last error is "ValueError: en_translation_parse_failed"
    And a run_dead_letter event is recorded
    And no second owner notice is staged

  Scenario: A later successful outcome in the same drive still succeeds
    Given a generation run whose first workflow outcome failed
    And a later workflow outcome in the same drive succeeded
    When the job handler finishes the run
    Then the run status is "succeeded"

  Scenario: A resume that only got stuck does not dead-letter the run
    Given a generation run whose resume was reverted to awaiting review as stuck
    When the job handler finishes the run
    Then the run status is "succeeded"
