Feature: NeonInput Component
  As a developer using the NeonInput component
  I want to render neon-styled text inputs
  So that forms match the Alter-Ego design system

  Scenario: Input shows placeholder text
    When I render a NeonInput with placeholder "Email"
    Then I should see an input with placeholder "Email"

  Scenario: Input applies neon text color
    When I render a NeonInput with aria-label "Email"
    Then the input should use the neon primary text color
