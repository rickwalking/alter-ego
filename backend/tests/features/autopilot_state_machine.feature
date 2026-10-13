Feature: Autopilot run state machine
  As the autopilot runner
  I want every run transition to be an allowed, conditional update
  So that a stale or illegal change cannot double-publish or skip the owner

  Scenario: Allowed transition persists and emits an event
    Given an autopilot run in state "queued"
    When the runner transitions it from "queued" to "generating"
    Then the run state is "generating"
    And one "content.autopilot.state_changed" outbox event exists

  Scenario: Concurrent transition loses the compare-and-set
    Given an autopilot run in state "awaiting_owner"
    And another actor already moved it to "publishing"
    When a second actor transitions it from "awaiting_owner" to "publishing"
    Then the transition returns false
    And no additional outbox event is written

  Scenario: Illegal transition is rejected
    Given an autopilot run in state "published"
    When a transition to "generating" is requested
    Then an InvalidAutopilotTransition error is raised

  Scenario: Missing run does not emit an event
    Given no autopilot run exists
    When the runner transitions it from "queued" to "generating"
    Then the transition returns false
    And no "content.autopilot.state_changed" outbox event exists
