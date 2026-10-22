Feature: New Post asks for a title before creating anything
  As the site owner
  I want "New Post" to open a form and create the draft only when I submit it
  So that an exploratory click never leaves an empty draft behind

  Scenario: Clicking New Post opens a form and creates nothing
    When I click "New Post"
    Then a "Create New Blog Post" form with a Title field opens
    And no blog post is created

  Scenario: Submitting the form creates the draft and opens the editor
    Given the New Post form is open
    When I enter the title "Agentes e o bug copiado" and click "Create"
    Then one draft titled "Agentes e o bug copiado" is created
    And the editor for that draft opens

  Scenario: The form cannot be submitted without a title
    Given the New Post form is open
    When the title is empty or only spaces
    Then "Create" is disabled and nothing is created

  Scenario: Cancelling the form creates nothing
    Given the New Post form is open
    When I click "Cancel"
    Then the form closes and no blog post is created

  Scenario: A failed create keeps the form open with the error
    Given the New Post form is open and the create request fails
    When I click "Create"
    Then the error is shown in the form and I can try again
