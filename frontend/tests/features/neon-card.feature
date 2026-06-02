Feature: NeonCard Component

  Scenario: Default card renders with dark background
    When I render a NeonCard with content
    Then I should see a card with background #0d1324
    And the card should have a subtle border

  Scenario: Card with title displays header
    When I render a NeonCard with a title
    Then I should see a card header with the title text

  Scenario: Clickable card has cursor pointer
    When I render a NeonCard with an onClick handler
    Then clicking should call the onClick handler
