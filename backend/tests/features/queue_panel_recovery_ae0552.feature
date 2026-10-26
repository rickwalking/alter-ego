Feature: Queue panel recovery accessibility and liveness
  Scenario: Row actions are named and confirmed by theme
    Given two queue rows with different theme titles
    When Pedro uses Cancel or Discard
    Then each accessible name includes its theme and confirmation is required

  Scenario: Polling stops on forbidden and running rows show liveness
    Given an editor receives 403 and a running row has started and heartbeat timestamps
    When polling and rendering continue
    Then no later request is made and started time and heartbeat age are visible

  Scenario: Running liveness is attributed only to the current project attempt
    Given running and queued generation rows and projects with distinct heartbeats
    When the queue board is read
    Then only the running row exposes its attributed heartbeat and lock version
    And generation update time and another attempt heartbeat are never substituted

  Scenario: Unstaged autopilot work appears immediately and only once
    Given Generate now and Reprocessar runs with and without staged generation rows
    When Telegram and the panel read the same queue
    Then every driven autopilot run appears exactly once in the same order
    And staged generation rows win dedupe races
    And projectless unstaged rows have no generation-run actions

  Scenario: A generating orphan has a safe project recovery target
    Given an old project-backed generating autopilot run has no generation row
    When the queue board is read
    Then a synthetic unstaged row identifies the project and permits reprocessing
    And its safe capability and refusal fields are present without raw last_error

  Scenario: Telegram and the panel share priority order and retry-aware estimates
    Given running, manual, ordinary, dispatched, undispatched and retry-waiting work
    When positions and start estimates are computed
    Then running leads and priority, job id and creation order break ties
    And running elapsed is subtracted and retry rejoin is a lower bound
    And retry-wait panel position is null while later estimates include its rejoin

  Scenario: Owner cancellation is audited without a Telegram failure alarm
    Given an owner cancellation and a genuine autopilot failure outbox event
    When Telegram notice kinds are selected
    Then owner cancellation has no failure notice kind
    And the genuine failure retains its notice and both events remain durable
