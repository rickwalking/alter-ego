Feature: NeonButton Component
  As a developer using the NeonButton component
  I want to render buttons in different variants, sizes, and states
  So that I can use consistent button UI across the application

  Background:
    Given the NeonButton component is rendered on a dark background

  Scenario: Primary variant renders with cyan gradient
    When I render a primary NeonButton with text "Submit"
    Then I should see a button with text "Submit"
    And the button should have a cyan gradient background

  Scenario: Disabled state prevents interaction
    Given a disabled NeonButton with an onClick handler
    When I click the button
    Then the onClick handler should NOT be called
    And the button should have the disabled attribute

  Scenario: Loading state shows spinner
    Given a NeonButton in loading state
    When I render the button
    Then I should see a spinner element inside the button
    And the button should be disabled
