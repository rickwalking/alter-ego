Feature: NeonBadge Component
  As a developer using the NeonBadge component
  I want to render status badges with neon variants
  So that I can show consistent labels across the dashboard

  Scenario: Cyan badge renders label text
    When I render a cyan NeonBadge with text "Active"
    Then I should see badge text "Active"

  Scenario: Dot indicator renders when enabled
    When I render a green NeonBadge with dot enabled
    Then a dot indicator should be visible inside the badge
