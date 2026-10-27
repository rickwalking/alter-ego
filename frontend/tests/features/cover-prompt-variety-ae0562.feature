@AE-0562 @frontend @dashboard
Feature: Varied cover-photo prompt suggestions
  Scenario: The six curated suggestions differ on every dimension
    Given a carousel with a topic and a palette
    When the owner looks at the cover prompt suggestions
    Then six suggestions are shown
    And no two share a location, an outfit, a pose, a shot or a light

  Scenario: Suggestions name colours in words, never hex codes
    Given a palette with hex colours
    Then no suggestion contains a hex code
    And the suggestions describe the palette's tones in words

  Scenario: The theme shows up as a prop, not as the quoted title
    Given the topic talks about AI agents
    Then each suggestion carries a different AI-related prop
    And no suggestion quotes the topic

  Scenario: Suggestions are stable per carousel and differ between carousels
    Given the same carousel id
    Then reloading shows the same six suggestions
    And another carousel id shows a different set

  Scenario: Outras ideias shuffles the catalogue without an AI call
    Given the curated suggestions are shown
    When the owner presses "Outras ideias"
    Then a new set of six suggestions is shown
    And no request is sent

  Scenario: Every suggestion fits the prompt field
    Then each suggestion is at most 400 characters
