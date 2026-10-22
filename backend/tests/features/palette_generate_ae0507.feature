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
