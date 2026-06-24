Feature: Responsive dashboard app shell (AE-0273)
  As a user on a phone or tablet
  I want the dashboard sidebar to collapse into an accessible drawer
  So that I can reach navigation without horizontal overflow

  Background:
    Given I am authenticated and viewing a dashboard route

  Scenario: Sidebar is an off-canvas drawer on mobile
    Given the viewport is 375px wide
    Then the sidebar is translated off-canvas
    And a menu button is visible

  Scenario: Opening the drawer traps focus and locks body scroll
    Given the viewport is 375px wide
    When I activate the menu button
    Then the sidebar slides into view
    And keyboard focus is trapped inside the sidebar
    And body scroll is locked

  Scenario: Escape closes the drawer and returns focus
    Given the drawer is open on mobile
    When I press Escape
    Then the drawer closes
    And focus returns to the menu button

  Scenario: Backdrop click closes the drawer
    Given the drawer is open on mobile
    When I click the backdrop outside the drawer
    Then the drawer closes

  Scenario: Navigating closes the drawer
    Given the drawer is open on mobile
    When the route changes
    Then the drawer closes

  Scenario: Persistent rail on desktop
    Given the viewport is 1280px wide
    Then the sidebar is a persistent rail
    And no menu button is shown
    And the content area is offset by the sidebar width

  Scenario: The sidebar width token stays in sync
    Then the CSS --sidebar-width equals the JS SIDEBAR_WIDTH_PX constant
