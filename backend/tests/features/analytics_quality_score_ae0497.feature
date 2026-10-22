Feature: The analytics quality score is real data or nothing
  As the site owner
  I want the quality score to be the average of real content scores
  So that I never read a number nobody measured

  Scenario: Without content scores the quality score is empty
    Given published and draft blog posts but no content quality score
    When the editorial analytics are read
    Then the quality score average is null and its count is 0

  Scenario: The quality score averages the content scores
    Given two content quality scores of 80 and 61
    When the editorial analytics are read
    Then the quality score average is 70.5 and its count is 2

  Scenario: Ad-hoc evaluations of pasted text are not counted
    Given a rubric evaluation of pasted text with the nil content id
    And one content quality score of 90
    When the editorial analytics are read
    Then the quality score average is 90.0 and its count is 1
