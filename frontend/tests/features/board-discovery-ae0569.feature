Feature: Workflow board discovery
  The owner can find and narrow carousels on the workflow board, the card
  order is stable, and card badges mean something.

  Background:
    Given the owner is on the workflow board at a desktop size

  Scenario: The board keeps a stable newest-first order
    When the board loads rows with distinct updated times
    Then every column lists its cards newest first
    And rows with the same updated time keep a deterministic id order

  Scenario: Search narrows the board
    When the owner types in the search box
    Then only cards whose title or topic match remain
    And matching ignores case and accents
    And pressing slash focuses the search box outside editable fields

  Scenario: Status chips filter by raw status
    When the owner presses a status chip
    Then only cards whose raw status maps to that bucket remain
    And the chip shows its count and pressed state
    And the filter is kept in the URL

  Scenario: Sort follows the toolbar
    When the owner chooses Title A-Z
    Then the cards sort by title
    And the default sort is Updated descending
    And the choice survives reload and Back through the URL

  Scenario: Badges use semantic colors
    When the board renders a card
    Then its badge variant and pulse come from the workflow status
    And Needs review reads magenta while In progress pulses cyan

  Scenario: Card titles are readable
    Given a card with empty title and topic
    When the board renders it
    Then its title is the untitled fallback
    And markup like asterisks or strong tags never shows in a title
    And a description equal to the title stays empty

  Scenario: The published column stops saying ready to publish
    Given a card in the published column
    When the board renders it
    Then it shows the relative updated time instead of a status badge

  Scenario: Column headers count the cards that need the owner
    Given a column with cards awaiting the owner
    When the board renders it
    Then its header shows the awaiting count next to the total
