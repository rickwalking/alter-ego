Feature: Reprocess a stuck carousel from the workspace and Fila

  Scenario: Reprocess shows progress after acceptance
    Given a stuck carousel in the workspace or Fila
    When the owner clicks Reprocessar
    Then one POST is sent and the returned run appears queued with position and ETA
    And later progress shows the running phase or a safe failure reason

  Scenario: Not stuck reasons are accessible
    Given work waiting for review, normally queued, or running with a fresh heartbeat
    When the Reprocessar control is presented
    Then it is disabled with a translated accessible reason

  Scenario: Rapid clicks cannot duplicate reprocess
    Given the first Reprocessar request is still pending
    When the owner clicks again
    Then no second request is sent and the existing run is shown

  Scenario: Failed phases keep Reprocessar visible
    Given the carousel workspace is showing a failed phase
    When the page renders
    Then Reprocessar remains available before the failure content

  Scenario: Process queue now is a panel action
    Given the Fila panel is visible to the owner
    When the owner clicks Processar fila agora
    Then the maintenance endpoint is called once and the board refreshes

  Scenario: Workspace reprocess errors are translated and safe
    Given a stale workflow version or a failed or forbidden reprocess request
    When the workspace handles the response
    Then it shows translated feedback without raw server details
    And a stale version refreshes the capability before another attempt

  Scenario: Workspace capability polling stops on forbidden
    Given the capability endpoint answers 403
    When the workspace renders
    Then no reprocess control or raw error is shown and no polling continues

  Scenario: Row actions are named and confirmed by theme
    Given two queue rows with different theme titles
    When the owner uses Cancel or Discard
    Then each accessible name includes its theme and confirmation is required

  Scenario: Polling stops on forbidden and running rows show liveness
    Given an editor receives 403 and a running row has started and heartbeat timestamps
    When polling and rendering continue
    Then no later request is made and started time and heartbeat age are visible
