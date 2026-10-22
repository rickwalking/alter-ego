Feature: Calendar "today" follows the viewer's local date
  As the site owner in Brazil (UTC-3)
  I want the calendar to highlight my local today and open on my local month
  So that after 21:00 it does not jump to tomorrow, which is the server's UTC date

  Scenario: The server render highlights no day
    Given the page is rendered on the server
    When the calendar HTML is produced
    Then no day cell is highlighted as today and no month grid is fixed yet

  Scenario: Today is the viewer's local date after the page loads
    Given it is 21:30 on 2026-10-21 in America/Sao_Paulo (00:30 on 2026-10-22 UTC)
    When the calendar loads in the browser
    Then the cell for the 21st is highlighted

  Scenario: The calendar opens on the viewer's local month at a month boundary
    Given the viewer's local date is 2026-10-31 while UTC is already 2026-11-01
    When the calendar loads in the browser
    Then the title reads "October 2026"

  Scenario: Today moves on at local midnight while the page stays open
    Given the calendar is open at 23:59:30 local time
    When the clock passes midnight
    Then the next day is highlighted

  Scenario: Month navigation is relative to the local month
    Given the calendar shows the local month
    When I click "Next month", then "Today"
    Then the title returns to the local month
