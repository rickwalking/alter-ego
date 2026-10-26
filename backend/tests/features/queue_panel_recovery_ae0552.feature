Feature: Queue panel recovery accessibility and liveness
  Scenario: Row actions are named and confirmed by theme
    Given two queue rows with different theme titles
    When Pedro uses Cancel or Discard
    Then each accessible name includes its theme and confirmation is required

  Scenario: Polling stops on forbidden and running rows show liveness
    Given an editor receives 403 and a running row has started and heartbeat timestamps
    When polling and rendering continue
    Then no later request is made and started time and heartbeat age are visible
