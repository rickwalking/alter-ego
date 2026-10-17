Feature: Dashboard dates follow the active locale (AE-0417)
  The dashboard is used in Portuguese, yet its dates were printed in English
  ("Oct 17, 2026" on the Posts do Blog cards). Every date the dashboard shows
  uses the active next-intl locale, with the same formats the public pages use
  (AE-0412): pt "17/10/2026", en "Oct 17, 2026".

  # --- Shared helper ---

  Scenario: A date is formatted in the active locale
    Given the date 2026-10-17
    When it is formatted for "pt"
    Then it reads "17/10/2026"
    When it is formatted for "en"
    Then it reads "Oct 17, 2026"

  Scenario: An unknown locale falls back to the default locale
    Given the date 2026-10-17
    When it is formatted for "fr"
    Then it reads "Oct 17, 2026"

  Scenario: An invalid or missing date prints nothing
    Given the value "not-a-date"
    When it is formatted for "pt"
    Then the result is empty

  Scenario: A date and time is formatted in the active locale
    Given the instant 2026-10-17 14:05 local time
    When it is formatted as a date and time for "pt"
    Then it reads "17/10/2026, 14:05"

  Scenario: A recent instant is shown as relative time in the active locale
    Given an instant 5 minutes ago
    When it is formatted as relative time for "pt"
    Then it reads "há 5 min."
    And an instant older than a day reads as a date

  # --- Surfaces ---

  Scenario: Posts do Blog cards show the date in Portuguese
    Given the active locale is "pt"
    And a blog post dated 2026-10-17
    When the dashboard blog list renders
    Then the card shows "17/10/2026"
    And never "Oct 17, 2026"

  Scenario: Blog cards keep the English format in the English UI
    Given the active locale is "en"
    And a blog post dated 2026-10-17
    When the dashboard blog list renders
    Then the card shows "Oct 17, 2026"

  Scenario: Workflow notifications show their time in the active locale
    Given the active locale is "pt"
    And a notification created at 2026-10-17 14:05
    When the notification center opens
    Then the notification shows "17/10/2026, 14:05"

  Scenario: The calendar names months and weekdays in the active locale
    Given the active locale is "pt"
    When the calendar shows October 2026
    Then the title reads "Outubro de 2026"
    And the weekday headers start with "dom."

  Scenario: Chat conversations show relative times in the active locale
    Given the active locale is "pt"
    And a conversation updated 3 hours ago
    When the chat list renders
    Then it shows "há 3 h"

  Scenario: Knowledge documents and admin users show dates in the active locale
    Given the active locale is "pt"
    When a document card or the user table shows a date of 2026-10-17
    Then it reads "17/10/2026"
