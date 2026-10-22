# language: en
@AE-0452 @backend
Feature: Rubric thresholds and prompt templates evaluate content correctly
  A criterion threshold is a fraction of the criterion's score scale (0.0-1.0,
  as the rubric API accepts it). Scores are compared on that same scale, and a
  stored legacy percentage threshold (e.g. 70.0) is read as 0.70.

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
