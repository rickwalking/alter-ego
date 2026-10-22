Feature: A quality rubric has at least one criterion
  As the site owner
  I want a rubric without criteria to be refused
  So that every saved rubric can actually score content

  Scenario: Creating a rubric without criteria is rejected
    When I create a rubric with an empty criteria list, or with no criteria at all
    Then the API answers 422
    And no rubric is stored

  Scenario: Updating a rubric to no criteria is rejected
    Given a rubric with one criterion
    When I update it with an empty criteria list
    Then the API answers 422
    And the rubric keeps its criterion

  Scenario: An update without criteria keeps the stored criteria
    Given a rubric with one criterion
    When I update only its name
    Then the API answers 200
    And the rubric keeps its criterion
