Feature: Background run writers never self-deadlock on the project row
  AE-0320: prod incident 2026-07-18 — every gate approval wedged because the
  resume runner awaited a separate-session heartbeat UPDATE that queued behind
  the runner's own uncommitted row lock, and the reaper's rescue flip queued on
  the same lock. Run-column writers are now lock-timeout-bounded and stage
  beats are single-attempt soft-fail; a dead run whose checkpoint advanced is
  converged by the drift reconciler instead of lingering as failed.

  Scenario: Heartbeat write is bounded by a lock timeout on Postgres
    Given a heartbeat write on a Postgres session
    When the write begins its transaction
    Then a transaction-scoped lock_timeout is applied before the UPDATE

  Scenario: Heartbeat write skips the lock timeout on SQLite
    Given a heartbeat write on a SQLite session
    When the write begins its transaction
    Then no lock_timeout statement is issued

  Scenario: Stage-boundary beat is single-attempt and never raises
    Given the run's main session may hold the project row lock
    When a stage-boundary heartbeat fails with a database error
    Then the beat returns false without retrying
    And the failure is logged as a heartbeat warning
    And the resume flow continues

  Scenario: Blocked reaper flip fails fast and retries next tick
    Given a stale run whose transaction still holds the project row lock
    When the reaper's atomic flip hits the lock timeout
    Then the reap returns false without wedging the worker tick
    And a carousel_run_reap_blocked warning is logged

  Scenario: Failed row behind an advanced parked checkpoint is converged
    Given a project row marked failed at phase "design"
    And the checkpoint is parked awaiting_human at phase "images"
    When the drift reconciler runs
    Then the row converges to phase "images" awaiting_human
    And lock_version and run_epoch are bumped and run columns cleared

  Scenario: Same-phase failure is left for the recovery UI
    Given a project row marked failed at phase "design"
    And the checkpoint is parked awaiting_human at phase "design"
    When the drift reconciler runs
    Then the row stays failed

  Scenario: Mid-step checkpoint never triggers phase convergence
    Given a project row marked failed
    And the checkpoint phase_status is in_progress
    When the drift reconciler runs
    Then the row stays failed
