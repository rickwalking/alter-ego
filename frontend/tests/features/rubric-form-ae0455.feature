# language: en
@AE-0455 @frontend @dashboard
Feature: Rubrics are created and edited in a real form
  The rubrics page lists the quality rubrics, explains an empty list, and
  creates or edits a rubric in a form that validates like the API does
  (name, content types, criteria with weight and threshold from 0 to 1).

  Scenario: An empty rubric list offers to create the first rubric
    Given the API has no rubrics
    When the editor opens the rubrics page
    Then the page explains what a rubric is
    And a "Create your first rubric" button opens the rubric form

  Scenario: A new rubric is created with its criteria
    Given the editor opened the new rubric form
    When they enter a name, keep "Carousel", add "Blog post" and add a criterion
    And they press "Create rubric"
    Then the API receives the name, both content types and the criterion
    And the page lists the new rubric

  Scenario: An existing rubric is edited and saved
    Given a rubric with one criterion
    When the editor presses "Edit" on that rubric
    Then the form shows the rubric's name, content types and criterion
    When they change the criterion weight and press "Save changes"
    Then the API receives an update for that rubric with the new weight

  Scenario: Criteria are added, reordered and removed
    Given the rubric form with two criteria
    When the editor moves the second criterion up
    Then it becomes the first criterion
    When they remove a criterion
    Then only the other criterion is left

  Scenario: Invalid fields block the save
    Given the new rubric form
    When the editor clears the name, unticks every content type and enters a weight of 2
    And they press "Create rubric"
    Then each invalid field shows its error and is marked invalid
    And nothing is sent to the API

  Scenario: A server refusal is shown in the form
    Given the API refuses the rubric with a message
    When the editor saves a valid rubric
    Then the API's message is shown in the form
    And the form stays open with the entered values

  Scenario: Cancel leaves the form without saving
    Given the editor changed the new rubric form
    When they press "Cancel" and confirm leaving
    Then the list is shown again
    And nothing is sent to the API

  Scenario: Unsaved changes ask before leaving
    Given the editor changed the rubric form
    When they press "Cancel" and decline leaving
    Then the form stays open with the entered values

  Scenario: Deleting a rubric asks first and explains a rubric in use
    Given a rubric in the list
    When the editor presses "Delete" and confirms
    Then the API deletes the rubric and the list no longer shows it
    When the API answers 409 because carousels or evaluations still use a rubric
    Then the delete dialog says, translated, that the rubric is still in use

  Scenario: The default rubric cannot be deleted from the list
    Given the default rubric in the list
    When the editor opens the rubrics page
    Then that rubric offers "Edit" but no "Delete"

  Scenario: A failed request keeps the API's own message
    Given the API answers a failed rubric request with a string detail
    When the rubrics collection request fails
    Then the error keeps the per-resource message and carries the API's detail and status
