Feature: Responsive dashboard listing & content pages (AE-0275)
  As a user browsing dashboard listings on a small screen
  I want card grids, search bars, and charts to reflow
  So that nothing overflows horizontally

  Scenario: Quick actions reflow
    Given the dashboard overview at 375px
    Then the quick-action cards stack to one column with no overflow

  Scenario: Search bar full width on mobile
    Given the personas page at 375px
    Then the search bar spans the available width

  Scenario: Card grid columns adapt
    Given a listing page at 375 / 768 / 1280px
    Then the cards render as 1 / 2 / 3 columns respectively

  Scenario: Analytics velocity chart never overflows the page
    Given the analytics page at 375px
    Then the velocity bar scrolls within its own track
    And the page has no horizontal overflow

  Scenario: Palettes grid fits a phone
    Given the palettes page at 375px
    Then palette cards render at least one-up with no horizontal overflow

  Scenario: Rubrics panel rows stay within the panel
    Given the rubrics page at 375px
    Then the 4-column rubric rows fit the panel width without page overflow
