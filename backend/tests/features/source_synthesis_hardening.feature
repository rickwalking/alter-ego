Feature: Source synthesis is resilient to malformed LLM responses
  AE-0318: a truncated/malformed LLM response during source synthesis must
  self-heal (one JSON repair retry) instead of self-poisoning (bad raw cached),
  and a failed workflow start must be observable (logged, specific detail).

  Scenario: Valid response is parsed and cached
    Given the LLM returns valid key-points JSON for a source
    When key points are extracted
    Then the findings are returned
    And the response is cached for reuse

  Scenario: Truncated response triggers one repair retry
    Given the LLM returns JSON truncated mid-string
    And the repair call returns the corrected JSON
    When key points are extracted
    Then the findings from the repaired JSON are returned
    And the malformed raw response is not cached

  Scenario: Repair failure fails closed with an observable error
    Given the LLM returns malformed JSON
    And the repair call also returns malformed JSON
    When the editorial workflow is started
    Then the response is 400 with the research synthesis failed detail
    And a workflow_start_failed error is logged with the project id

  Scenario: Retry after a transient malformed response is not poisoned
    Given a first extraction attempt failed on malformed JSON
    When the same source is extracted again
    Then a fresh LLM call is made
    And a valid response this time yields findings

  Scenario: Poisoned cache entry from a previous deploy is evicted
    Given the cache contains an unparseable raw response for a source prompt
    When key points are extracted for that source
    Then the poisoned entry is evicted
    And a fresh LLM call is made
