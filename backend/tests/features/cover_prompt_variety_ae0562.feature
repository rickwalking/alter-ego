@AE-0562 @backend
Feature: Varied AI cover-photo prompt ideas ("Mais ideias")
  Scenario: The prompt asks for ideas distinct on every visual dimension
    When the ideas prompt is rendered
    Then it asks for different location, wardrobe, pose, angle and light per idea
    And it asks for the theme as props or metaphors, colour words and no hex codes

  Scenario: Ideas sharing a location and a pose are dropped
    Given the model returns two ideas with the same location and pose
    Then only the first of them is kept

  Scenario: A repeated combination with too few left triggers the one retry
    Given the first answer keeps fewer than three distinct ideas
    Then the service asks once more and merges the distinct ideas

  Scenario: Ideas with hex codes are rejected
    Given the model returns an idea containing "#0b0b14"
    Then that idea is dropped
