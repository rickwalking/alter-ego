Feature: Workflow board layout and navigation
  The desktop workflow board fits one viewport, columns scroll on their own,
  and a round trip into a carousel keeps the user's place.

  Background:
    Given the owner is on the workflow board at a desktop size

  Scenario: The board fits the screen and columns scroll independently
    When the board renders with more cards than fit the viewport
    Then the board area does not grow the page vertically
    And each column keeps its own scrolling card list with its header visible

  Scenario: Empty and done columns collapse to rails
    When the board renders with empty columns and the done columns Published and Rejected
    Then those columns appear as vertical rails showing only the name and count
    And every rail is a labelled button that expands its column

  Scenario: Expanded rails persist across reloads
    When the owner expands a rail into a column
    Then the expanded column is remembered in localStorage across reloads

  Scenario: An expanded empty column explains itself
    When the owner expands an empty column
    Then the column shows the empty-column text

  Scenario: The breadcrumb links back to the board
    When a page renders a breadcrumb item that carries a link
    Then that item is a real link with a visible focus style
    And the current (last) item is not a link

  Scenario: Returning from a carousel restores the board scroll
    When the owner opens a card and comes back to the board
    Then the board restores its horizontal position and the column scroll positions

  Scenario: The carousel workspace marks the board active
    When the owner is on a carousel workspace page
    Then the Workflow Board sidebar item is active
    And the create wizard page does not mark it active

  Scenario: Previous and next controls follow the board column sequence
    Given the owner opened a carousel from a board column
    When the carousel workspace renders
    Then previous and next controls follow that column's ordered cards
    And the current position and column name are visible
    And the bracket keys navigate unless the owner is editing text
