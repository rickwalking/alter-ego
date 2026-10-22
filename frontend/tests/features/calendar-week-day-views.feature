Feature: Calendar week and day views
  The dashboard content calendar has working Month, Week and Day views. The
  toolbar state (view and focused date) lives in the URL, so a reload or a
  shared link shows the same range. All views read the same content-calendar
  data, place items on the viewer's local date and show local times.

  Background:
    Given I am viewing the dashboard content calendar

  Scenario: The calendar opens on the month view by default
    Given the URL has no view parameter
    When the calendar loads
    Then the Month button is pressed
    And the month grid is shown

  Scenario: An unknown view in the URL falls back to the month view
    Given the URL has "?view=year"
    When the calendar loads
    Then the month grid is shown

  Scenario: Switching to the week view shows the focused week
    Given today is Wednesday 2026-10-21
    When I press "Week"
    Then the URL has "?view=week"
    And the title reads "Oct 18 – 24, 2026"
    And seven day columns from Sunday Oct 18 to Saturday Oct 24 are shown

  Scenario: Switching to the day view shows the focused day
    Given today is Wednesday 2026-10-21
    When I press "Day"
    Then the URL has "?view=day"
    And the title reads "Wednesday, October 21, 2026"

  Scenario: The view and date are restored from the URL
    Given the URL has "?view=day&date=2026-10-30"
    When the calendar loads
    Then the Day button is pressed
    And the title reads "Friday, October 30, 2026"

  Scenario: Previous and next move by one week in the week view
    Given the URL has "?view=week&date=2026-10-21"
    When I press "Next week"
    Then the URL has "?view=week&date=2026-10-28"
    When I press "Previous week"
    Then the URL has "?view=week&date=2026-10-21"

  Scenario: Previous and next move by one day in the day view
    Given the URL has "?view=day&date=2026-10-21"
    When I press "Next day"
    Then the URL has "?view=day&date=2026-10-22"
    When I press "Previous day"
    Then the URL has "?view=day&date=2026-10-21"

  Scenario: Today returns to the current day and drops the date from the URL
    Given the URL has "?view=week&date=2026-12-02"
    When I press "Today"
    Then the URL has "?view=week"

  Scenario: A week day header opens that day in the day view
    Given the week view of 2026-10-18 to 2026-10-24
    When I activate the header of Thursday Oct 22
    Then the URL has "?view=day&date=2026-10-22"

  Scenario: Back returns to the previous view
    Given the week view of 2026-10-18 to 2026-10-24
    When I open Thursday Oct 22 in the day view
    And I press the browser's Back button
    Then the week view of 2026-10-18 to 2026-10-24 is shown again
    And previous, next and Today do not add history entries

  Scenario: An item without a title is listed as untitled
    Given an item with an empty title on 2026-10-21
    When I open the day view of 2026-10-21
    Then the item is listed as "Untitled"

  Scenario: The week view fetches only its own days
    Given the URL has "?view=week&date=2026-10-21"
    When the calendar loads
    Then the content calendar is requested from Oct 17 to Oct 25 (one day of padding on each side)

  Scenario: Week and day items show their local time
    Given a blog post with event_date "2026-10-22T01:00:00Z"
    And the viewer's timezone is America/Sao_Paulo
    When I open the day view of 2026-10-21
    Then the item is listed with its time "10:00 PM", its type and its status, labelled like the month grid

  Scenario: A date-only item is listed as all day
    Given an item with event_date "2026-10-21"
    When I open the day view of 2026-10-21
    Then the item is listed as "All day"

  Scenario: An empty day says nothing is scheduled
    Given no items on 2026-10-21
    When I open the day view of 2026-10-21
    Then I see "Nothing scheduled for this day"

  Scenario: The view switch is keyboard operable and announces the active view
    Given the calendar is in the month view
    When I tab to "Week" and press Enter
    Then the week view is shown
    And "Week" has aria-pressed true and "Month" has aria-pressed false

  Scenario: Week and day labels follow the active locale
    Given the locale is pt
    Then the week title for 2026-10-21 reads "18 – 24 de out. de 2026"
    And the day title reads "Quarta-feira, 21 de outubro de 2026"
