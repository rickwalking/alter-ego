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
    When the rubric id is not a UUID
    Then the request is refused with 422

  Scenario: Every content prompt carries the rubric's criteria
    Given a carousel with the QA rubric
    When a slide is drafted with the generic, Radar, POV or POV news prompt
    Then the prompt carries the rubric name and each criterion's name, description, guidance, scale and threshold
    And the rubric is framed as reference data, before the content prompt and its output instructions
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
    When the content phase runs again without new drafts, or regenerates the same text
    Then no judge call is made

  Scenario: A judge failure leaves the run going without scores
    When the judge never answers usable JSON, answers JSON of the wrong shape, hits a provider error or runs past its timeout
    Then the content phase keeps its drafts, has no rubric_scores and the workflow goes on
    And the judge made exactly one call on one model (no retry, no fallback)

  Scenario: A failed re-score of regenerated drafts drops the old scores
    Given a carousel already scored
    When its content is regenerated and the judge fails
    Then rubric_scores is emptied and the carousel's score row is removed

  Scenario: A rubric used by a carousel cannot be deleted
    Given a carousel created with the QA rubric
    When the owner deletes the QA rubric
    Then the request is refused with 409 naming the carousel
    And the rubric still exists
    And a default rubric in use also answers 409 naming its carousels
    And an editor sees only their own carousels and a count of the others, an admin sees them all

  Scenario: The quality average counts only the caller's own content
    Given scores of a carousel owned by the editor and of one owned by someone else
    When the editor reads the analytics summary
    Then the quality average counts only the editor's carousel
    And an admin's average counts both
    And a blog post's score counts for its author
    And a caller with no scored content reads "no data"

  Scenario: Autopilot and chat carousels get the default carousel rubric
    Given a default rubric for carousels
    When the autopilot or the chat creates a carousel
    Then it is created with the default carousel rubric

  Scenario: A rubric's criteria are bounded before they reach a prompt
    When a rubric is saved with a criterion description or guidance over 1,000 characters, or more than 12 criteria
    Then the request is refused with 422
    And criterion text reaching a prompt is stripped of injection phrases and markup
    And rubrics stored before the bounds still load

  Scenario: Stored scores keep the rubric version they were given under
    When a rubric is edited
    Then its version goes up
    And a score records the rubric version and each criterion's description, scale, weight and threshold as scored

