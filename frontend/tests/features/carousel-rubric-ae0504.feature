Feature: The owner picks the quality rubric of a carousel and sees its scores
  As the owner creating and reviewing a carousel
  I want to choose the rubric it is written against and see how each criterion scored
  So that I know before publishing whether it meets my quality bar

  Scenario: The wizard preselects the default carousel rubric
    Given rubrics for carousels, one of them the default, and a rubric for blog posts only
    When the owner opens the create wizard
    Then "Rubrica de qualidade" offers "Rubrica padrão" (the server's default), the carousel rubrics and "Sem rubrica"
    And once the list loads the default rubric is preselected and marked as the default

  Scenario: The chosen rubric is sent with the carousel
    When the owner picks a rubric and creates the carousel
    Then the request carries its rubric_id
    When the owner picks "Política padrão (sem rubrica)"
    Then the request carries rubric_id null
    And before any choice the request leaves rubric_id out (the server default)

  Scenario: Final review shows each criterion's score against its threshold
    Given the carousel was scored against its rubric
    When the owner opens "Qualidade" in Revisão final
    Then the rubric name and the overall score out of 100 are shown
    And each criterion shows its score and its minimum
    And a criterion below its minimum is flagged

  Scenario: Final review without rubric scores
    Given the carousel has no rubric scores, or scores without an overall score
    When the owner opens "Qualidade"
    Then the empty note is shown
