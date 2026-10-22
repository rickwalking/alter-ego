Feature: A carousel is drafted and scored against the quality rubric chosen for it
  As the owner creating a carousel
  I want to pick the quality rubric it is written and judged against
  So that the draft aims at my criteria and I see how it scored before publishing

  Background:
    Given a default rubric for carousels and the QA rubric with two 0-100 criteria

  Scenario: A carousel created without a rubric gets the default carousel rubric
    When the owner creates a carousel without rubric_id
    Then the carousel stores the default carousel rubric

  Scenario: The owner picks a rubric or none in the wizard
    When the owner creates a carousel with the QA rubric
    Then the carousel stores the QA rubric
    When the owner creates a carousel with rubric_id null
    Then the carousel has no rubric

  Scenario: A rubric that cannot be used is refused at create
    When the owner creates a carousel with an unknown rubric id
    Then the request is refused with 404
    When the owner creates a carousel with a rubric that only applies to blog posts
    Then the request is refused with 422

  Scenario: Every content prompt carries the rubric's criteria
    Given a carousel with the QA rubric
    When a slide is drafted with the generic, Radar, POV or POV news prompt
    Then the prompt ends with the rubric name and each criterion's name, description, guidance, scale and threshold
    And without a rubric the prompt is unchanged

  Scenario: The drafted carousel is scored on 0-100 per criterion
    Given drafted slides of a carousel with the QA rubric
    When the judge scores them
    Then each criterion has a 0-100 score, its threshold and whether it passed
    And the overall score is the weighted average, rounded
    And the scores are in rubric_scores and in the carousel's only rubric_evaluation_scores row

  Scenario: A criterion below its threshold is flagged
    Given the judge scored one criterion below its threshold
    Then that criterion is marked as not passed and the carousel does not pass

  Scenario: A regeneration replaces the scores, an unchanged draft keeps them
    Given a carousel already scored
    When its content is regenerated
    Then the new scores replace the old row
    When the content phase runs again without new drafts
    Then no judge call is made

  Scenario: A judge failure leaves the run going without scores
    When the judge never answers usable JSON
    Then the content phase has no rubric_scores and the workflow goes on

  Scenario: A rubric used by a carousel cannot be deleted
    Given a carousel created with the QA rubric
    When the owner deletes the QA rubric
    Then the request is refused with 409 naming the carousel
    And the rubric still exists

  Scenario: The quality average counts only the caller's own content
    Given scores of a carousel owned by the editor and of one owned by someone else
    When the editor reads the analytics summary
    Then the quality average counts only the editor's carousel
    And an admin's average counts both
