Feature: Image prompt review
  As a content reviewer
  I want to inspect the image prompts created for each carousel slide
  So that I can approve or revise the visual direction before images are generated

  Scenario: Review prompts on the images tab before approving
    Given an editorial workflow is awaiting review on the images tab
    And the workflow state contains image prompts for each slide
    When I open the images tab
    Then I should see the slide image prompts
    And each prompt should include the slide title and generated prompt text
    And the prompt text should be read-only

  Scenario: Hide prompt review when no image prompts are available
    Given an editorial workflow is awaiting review on the images tab
    And the workflow state does not contain slide image prompts
    When I open the images tab
    Then I should not see the slide image prompt review

  Scenario: Keep prompt review scoped to the images tab
    Given an editorial workflow state contains slide image prompts
    When I open a non-image workflow tab
    Then I should not see the slide image prompt review
