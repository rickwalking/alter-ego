Feature: Sync the calendar now
  The calendar's "Sync" button re-fetches the content calendar for the range
  on screen, so posts scheduled or published elsewhere show up without a page
  reload.

  Background:
    Given I am viewing the dashboard content calendar

  Scenario: Sync re-fetches the visible range
    When I press "Sync"
    Then the content calendar for the visible range is requested again

  Scenario: Sync shows that it is running
    When I press "Sync"
    Then the button reads "Syncing…", is busy and cannot be pressed again until the request ends

  Scenario: A finished sync shows when it happened
    Given the sync finished at 14:05 local time
    Then I see "Synced at 2:05 PM"

  Scenario: A failed sync does not claim to be up to date
    Given the sync request failed or was aborted
    Then the load error is shown
    And no new "Synced at" time is recorded

  Scenario: Sync is labelled in the active locale
    Given the locale is pt
    Then the button reads "Sincronizar"
