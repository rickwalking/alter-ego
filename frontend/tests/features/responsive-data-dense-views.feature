Feature: Responsive data-dense dashboard views (AE-0276)
  As a user on a small screen
  I want the calendar, chat, and kanban to adapt
  So that dense layouts stay usable without page overflow

  Scenario: Calendar scrolls on mobile without crushing cells
    Given the calendar at 375px
    Then the month grid scrolls horizontally with snap
    And each day cell stays at least 80px wide

  Scenario: Chat conversation list is a drawer on mobile
    Given the chat page at 375px
    Then the conversation list is an off-canvas drawer
    And the chat area is full width
    And a conversations toggle is visible

  Scenario: Selecting a conversation closes the chat drawer
    Given the chat drawer is open on mobile
    When I select a conversation
    Then the drawer closes

  Scenario: Chat drawer is keyboard accessible
    Given the chat drawer is open on mobile
    When I press Escape
    Then the drawer closes and focus returns to the toggle

  Scenario: Chat pane is persistent on desktop
    Given the chat page at 1280px
    Then the 280px conversation pane is always visible with no toggle

  Scenario: Kanban columns snap-scroll on mobile
    Given the workflow board at 375px
    Then columns are a fixed 280px width and scroll-snap horizontally
