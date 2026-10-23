@AE-0507 @backend @palettes
Feature: Generate palette candidates from a description
  As the owner creating a palette
  I want three contrast-checked candidates from a short description
  So that I can start from a readable palette instead of picking hex values by hand

  Scenario: A description returns three validated candidates
    Given the fast LLM answers three well-formed palettes
    When the owner posts a description to the palette generator
    Then three candidates are returned with name, colours, mode and keywords
    And nothing is saved to the catalog

  Scenario: A low-contrast colour is repaired before it is returned
    Given the fast LLM answers a palette whose accent is too close to the background
    When the owner posts a description to the palette generator
    Then the returned accent reaches 4.5:1 against the background
    And the slide ink and the primary colour reach 4.5:1 against the background

  Scenario: The mode follows the background
    Given the fast LLM answers a light background labelled as dark
    When the owner posts a description to the palette generator
    Then the candidate mode is light

  Scenario: Invalid candidates are dropped
    Given the fast LLM answers one valid palette, one with a non-hex colour and one with an unsafe name
    When the owner posts a description to the palette generator
    Then only the valid candidate is returned

  Scenario: Brand keywords are dropped from a candidate
    Given the fast LLM answers a palette whose keywords include a root brand keyword
    When the owner posts a description to the palette generator
    Then the candidate keywords leave the brand keyword out

  Scenario: The generator is unavailable when the LLM fails
    Given the fast LLM raises an error or answers text that is not JSON
    When the owner posts a description to the palette generator
    Then the response is 503 with "palette_generation_unavailable"

  Scenario: A too short description is rejected
    When the owner posts a two-character description to the palette generator
    Then the response is 422 and the LLM is not called

  Scenario: The generator needs a logged-in user
    Given no logged-in user
    When a description is posted to the palette generator
    Then the response is 401

  Scenario: The generator is rate limited
    Given the owner generated palettes five times in the last minute
    When the owner posts a description to the palette generator again
    Then the response is 429 and the LLM is not called

  Scenario: The generator is rate limited per user
    Given one user generated palettes five times in the last minute
    When another user posts a description to the palette generator
    Then that user still gets candidates

  Scenario: Missing or malformed keywords are an empty list
    Given the fast LLM answers a palette whose keywords are missing, null or not a list
    When the owner posts a description to the palette generator
    Then the candidate is returned with no keywords

  Scenario: A short answer is completed by one more call
    Given the fast LLM's first answer has fewer than three valid candidates
    When the owner posts a description to the palette generator
    Then the LLM is asked once more and its new candidates are added, up to three
    And a failing second call keeps the first answer's candidates

  Scenario: Repeated candidates are dropped
    Given the fast LLM answers two candidates with the same name or the same colours
    When the owner posts a description to the palette generator
    Then only the first of them is returned

  Scenario: The model call carries the token cap and temperature
    Given the fast chat model of the palette generator
    When it answers a palette prompt
    Then the call to the model carries the generation's max tokens and temperature
