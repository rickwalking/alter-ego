Feature: The content calendar is a proper accessible table
  As a screen-reader or keyboard user of the content calendar
  I want the month to be announced as a table of week rows with weekday headers and a page heading
  So that I can read days by row and column, tab past the month quickly and know which page I am on

  Scenario: The month is a named table of week rows
    Given the calendar shows October 2026
    Then a table named "October 2026" holds a header row of 7 weekday column headers
    And every day cell sits inside a week row of 7 cells

  Scenario: The read-only month adds no tab stops
    Given the calendar shows a month with a scheduled item
    Then no day cell or chip is focusable
    And no chip is announced as a button

  Scenario: An empty month is still a valid table
    Given a month with no scheduled content
    Then the empty-month message sits in a row-wide cell spanning 7 columns

  Scenario: The calendar page has a level-1 heading
    Then the calendar header's title is the page's level-1 heading

  Scenario: Placeholder titles fall back to the localized Untitled
    Given a calendar item titled "slide" or "Slide 3"
    Then its chip reads "Untitled"

  Scenario: Calendar dim text meets WCAG AA contrast
    Given the calendar's dim text colour on its header and card backgrounds
    Then its contrast ratio is at least 4.5:1
