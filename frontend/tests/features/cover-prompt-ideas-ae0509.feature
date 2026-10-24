@AE-0509 @frontend @dashboard
Feature: Prompt suggestions for a new cover photo
  Scenario: The Slide 1 photo shows curated suggestions for the topic and palette
    Given a Ponto de Vista carousel with a topic and a palette in the create form
    When the owner looks at "Foto do slide 1"
    Then six curated prompt suggestions are shown under the prompt field
    And they mention the palette's colours and the topic

  Scenario: Without a palette or a topic the suggestions stay generic
    Given the theme is "auto" and the topic is empty
    Then the curated suggestions use neutral colours and no topic

  Scenario: Tapping a suggestion fills the prompt field, which stays editable
    Given the curated suggestions are shown
    When the owner taps one
    Then the prompt field holds its text
    And the owner can still edit the prompt

  Scenario: More ideas asks the AI with only the topic and the palette
    Given a topic of at least three characters
    When the owner presses "Mais ideias"
    Then the request carries only the topic, the palette and the dashboard locale
    And the AI ideas replace the curated suggestions

  Scenario: More ideas needs a topic
    Given the topic is shorter than three characters
    Then "Mais ideias" is disabled with a hint to write the topic

  Scenario: A failed AI call keeps the curated suggestions
    Given the ideas request fails
    When the owner presses "Mais ideias"
    Then a retryable error is shown and the curated suggestions stay
