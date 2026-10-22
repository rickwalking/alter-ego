@AE-0452 @frontend
Feature: Failed background actions are shown, never swallowed
  A click that starts a request must show its failure in the UI. A rejected
  promise that nobody handles leaves the user with no feedback.

  Scenario: A failed "mark as read" is shown in the notification panel
    Given the notification panel lists an unread notification
    When marking it as read fails
    Then the panel shows the "mark as read failed" message
    And the notification stays unread

  Scenario: A failed key-point extraction is shown on the source materials panel
    Given the source materials panel lists a source
    When extracting its key points fails
    Then the panel shows the extraction error

  Scenario: A failed create is shown on the personas and rubrics pages
    Given the collection page has loaded
    When creating an item fails
    Then the create error is shown
    And the list is not reloaded

  Scenario: A successful reload clears an earlier load error
    Given loading the collection failed once
    When the collection reloads successfully
    Then no error is shown and the items are listed
