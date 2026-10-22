# language: en
@AE-0498 @frontend @dashboard
Feature: The rubric form needs at least one criterion
  Scenario: A rubric without criteria cannot be saved
    Given the new rubric form with a name and a content type but no criteria
    When the editor presses "Create rubric"
    Then the criteria section shows "Adicione ao menos um critério."
    And nothing is sent to the API

  Scenario: Adding a criterion clears the block
    Given the form showed the missing-criterion message
    When the editor adds a named criterion and presses "Create rubric"
    Then the rubric is sent with that criterion
