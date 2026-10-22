@AE-0452 @frontend
Feature: The workflow board refresh keeps a steady error and the newest data
  The board refreshes on a poll and on window focus. A failure message must
  not vanish and reappear on every failed poll, and an older response must not
  replace a newer one.

  Scenario: Repeated failed refreshes keep the error shown
    Given the board refresh has failed
    When the next poll starts and fails again
    Then the error stays shown the whole time
    And it clears only when a refresh succeeds

  Scenario: An older refresh answering late does not replace newer data
    Given a poll and a focus refresh are in flight
    When the newer refresh answers first and the older one answers after it
    Then the board shows the newer data
