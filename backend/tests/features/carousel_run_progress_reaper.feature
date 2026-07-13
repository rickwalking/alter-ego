Feature: Revision-run progress visibility
  While a carousel revision/generation run executes (~13-15 minutes observed
  in prod), the client shows a live "revision in progress" state instead of
  enabled buttons that fail with an opaque 409, and operators can tell a slow
  healthy run from a stuck workflow at a glance (AE-0315).

  Scenario: User sees a live in-progress banner during a revision
    Given a content revision run was accepted
    When the user views any step of the create flow
    Then a banner shows the running phase and elapsed time
    And approve and revise actions are disabled

  Scenario: Resume attempt during a run explains itself
    Given a revision run is in progress
    When the client submits a resume request
    Then the response is 409 with a run-in-progress code and run_started_at
    And the UI shows the in-progress banner instead of an error toast

  Scenario: Banner clears when the run finishes
    Given the in-progress banner is visible
    When the run publishes run.finished on the workflow stream
    Then the banner clears and review actions re-enable
    And the regenerated content is shown

  Scenario: Overdue run is flagged for operators
    Given a run has exceeded the configured maximum duration
    When the workflow watchdog ticks
    Then a run_overdue alert is logged with the elapsed time

  Scenario: Dead run is reaped and the user recovers without an operator
    Given a backend restart killed a revision run mid-flight
    And the project row says in_progress with a stale run_heartbeat_at
    When the watchdog tick runs past the heartbeat threshold
    Then the cancellation marker is set before any row transition
    And the row is reconciled to awaiting_human
    And run.finished with a stale reason is published on the stream
    And the user's next resume attempt is accepted

  Scenario: Slow healthy run is alerted but never reaped
    Given a revision run alive for 70 minutes with fresh heartbeats
    When the watchdog tick runs
    Then a run_overdue alert is emitted
    And the row remains in_progress and the run continues undisturbed
