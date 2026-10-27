Feature: Workspace generation timeline
  The carousel workspace presents generation history compactly and accessibly in
  Portuguese and English while reusing the workflow's existing live updates.

  Scenario: Generation log groups runs and phases accessibly
    Given multiple runs with repeated phase attempts and a failed event
    When the owner opens the generation log
    Then the newest run is first and older runs are collapsed
    And events are grouped by run and phase with right-aligned durations
    And failure meaning is conveyed by text as well as color
    And run disclosures and load more are keyboard accessible

  Scenario: Generation log refreshes from existing workflow updates
    Given an active generation run and the existing workflow SSE or polling state
    When a workflow update arrives
    Then the generation log query is invalidated and shows new events
    And no additional polling interval or SSE connection is created

  Scenario: Generation log supports empty error and trace states
    Given a carousel without generation events
    When the owner opens the log
    Then a localized empty state is shown
    When loading more fails or a trace link exists
    Then the existing entries stay visible with a localized error or trace link
