# language: en
@AE-0452 @backend
Feature: Rubric thresholds and prompt templates evaluate content correctly
  A criterion threshold is a fraction of the criterion's score scale (0.0-1.0,
  as the rubric API accepts it). Scores are compared on that same scale, and a
  stored legacy threshold (70.0 on 0-100, 7.0 on 1-10) is read as 0.70. Only
  reads normalise: create and update reject a threshold above 1.0.

  Scenario: A score below the threshold fails the criterion
    Given a 0-100 criterion with threshold 0.7
    When the content scores 69.9
    Then the criterion fails and improvement suggestions are generated

  Scenario: A score at the threshold passes the criterion
    Given a 0-100 criterion with threshold 0.7
    When the content scores 70
    Then the criterion passes and no suggestions are generated

  Scenario: A 1-10 criterion compares on its own scale
    Given a 1-10 criterion with threshold 0.8
    When the content scores 7
    Then the criterion fails

  Scenario: A legacy percentage threshold is read as a fraction
    Given a stored rubric whose criterion threshold is 70.0
    When the rubrics are listed
    Then the listing succeeds and the threshold reads 0.7

  Scenario: A legacy threshold on a 1-10 criterion is read on its own scale
    Given a stored 1-10 criterion whose threshold is 7.0
    When the threshold is normalised
    Then it reads 0.7

  Scenario: A legacy threshold above the scale maximum is read as a percentage
    Given a stored 1-10 criterion whose threshold is 70.0, or a 0-100 one whose threshold is 150.0
    When the threshold is normalised
    Then it reads 0.7, and never more than 1.0

  Scenario: Creating or updating a rubric with a threshold above 1.0 is rejected
    Given a rubric payload whose criterion threshold is 1.5, 7 or 70
    When it is created or updated
    Then the API answers 422 and nothing is stored

  Scenario: An edited legacy rubric saves
    Given a stored 0-100 rubric whose criterion threshold is 70.0
    When the rubric is read and its criteria are saved back unchanged
    Then the save answers 200 and the stored threshold is 0.7

  Scenario: The default editorial rubric uses fraction thresholds
    When the default rubric criteria are built
    Then every threshold is between 0 and 1

  Scenario: A prompt template with other braces does not crash the evaluation
    Given a criterion prompt template with "{content}" and a literal JSON example in braces
    When the criterion is evaluated
    Then the content is substituted and the literal braces are kept

  Scenario: Content that contains a placeholder is not substituted again
    Given content that contains the text "{sources}"
    When the criterion is evaluated
    Then the content appears unchanged in the prompt
