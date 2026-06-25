Feature: Calendar month navigation
  The dashboard content calendar reflects a real, navigable month instead of a
  static "May 2026" mockup. The grid, title, and event placement follow the
  viewed month, which defaults to the current month.

  Background:
    Given I am viewing the dashboard content calendar

  Scenario: Calendar opens on the current month
    Given today is in June 2026
    When the calendar loads
    Then the title reads "June 2026"
    And today's date cell is highlighted

  Scenario: Navigating to the next month
    Given the calendar shows "June 2026"
    When I click "Next month"
    Then the title reads "July 2026"
    And the grid shows July's days aligned to the correct weekday columns

  Scenario: Navigating to the previous month
    Given the calendar shows "June 2026"
    When I click "Previous month"
    Then the title reads "May 2026"

  Scenario: Returning to the current month
    Given the calendar shows a month other than the current one
    When I click "Today"
    Then the title returns to the current month
    And today's date cell is highlighted again

  Scenario Outline: Month length is rendered correctly
    Given the viewed month is "<month>"
    When the grid is built
    Then it shows <days> in-month day cells

    Examples:
      | month         | days |
      | January 2026  | 31   |
      | February 2026 | 28   |
      | February 2028 | 29   |

  Scenario: Events appear on their real date
    Given a carousel is scheduled for 2026-07-10
    When I navigate to July 2026
    Then the event appears on the 10th
    And it does not appear in June or August

  Scenario: A UTC time component does not shift an event's day
    Given an item with event_date "2026-07-10T23:30:00Z"
    When the July 2026 grid is built
    Then the event is placed on the 10th regardless of local timezone
