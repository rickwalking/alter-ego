# language: en
@AE-0455 @frontend @dashboard
Feature: Personas are created and edited in a real form
  The personas page creates or edits a persona in a form with every voice
  field the API stores (name, description, expertise, tone, style, phrases,
  writing samples) and validates it like the API does.

  Scenario: An empty persona list offers to create the first persona
    Given the API has no personas
    When the editor opens the personas page
    Then the page explains what a persona is
    And a "Create your first persona" button opens the persona form

  Scenario: A new persona is created with its voice fields
    Given the editor opened the new persona form
    When they enter a name, expertise areas, a tone, phrases and a writing sample
    And they press "Create persona"
    Then the API receives every field, with blank text sent as null
    And the page lists the new persona

  Scenario: An existing persona is edited and saved
    Given a persona with expertise, phrases and a writing sample
    When the editor presses "Edit" on that persona
    Then the form shows the persona's stored values
    When they remove a forbidden phrase and press "Save changes"
    Then the API receives an update for that persona without that phrase

  Scenario: Invalid fields block the save
    Given the new persona form
    When the editor leaves the name empty and adds an empty writing sample
    And they press "Create persona"
    Then each invalid field shows its error and is marked invalid
    And nothing is sent to the API

  Scenario: A server refusal is shown in the persona form
    Given the API refuses the persona with a message
    When the editor saves a valid persona
    Then the API's message is shown in the form
    And the form stays open with the entered values

  Scenario: Cancel asks before discarding persona changes
    Given the editor changed the persona form
    When they press "Cancel" and decline leaving
    Then the form stays open with the entered values
    When they press "Cancel" and confirm leaving
    Then the list is shown again

  Scenario: Deleting a persona asks first
    Given a persona in the list
    When the editor presses "Delete" and confirms
    Then the API deletes the persona and the list no longer shows it

  Scenario: Deleting a persona still in use explains why
    Given a persona that carousels or voice corrections still use
    When the editor presses "Delete" and confirms
    And the API answers 409
    Then the delete dialog says, translated, that the persona is still in use
    And the persona stays in the list

  Scenario: A search without matches says so
    Given personas in the list
    When the editor searches for a name no persona has
    Then the page says there are no results for that search
