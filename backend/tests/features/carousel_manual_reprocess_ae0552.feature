Feature: Owners reprocess stuck carousels through the generation queue
  Manual recovery never runs a phase in the web process. It uses CAS and the queue,
  skips the autopilot daily cap and backlog, and kicks the worker without preempting
  the current drive.

  Scenario: A dead letter is reprocessed through the queue
    Given an owner carousel with a dead-letter generation run
    When the owner clicks Reprocessar
    Then the run is queued with manual priority and the worker is kicked
    And an audit event is stored without content text

  Scenario: Retry wait becomes eligible immediately
    Given a generation run waiting for a delayed retry
    When the owner clicks Reprocessar
    Then its status and transport delay become eligible now
    And its domain attempt budgets are unchanged

  Scenario: A stale running row is taken over safely
    Given a running generation row whose heartbeat is older than the reaper threshold
    And no live driver holds the project drive lock
    When the owner clicks Reprocessar
    Then the run is queued once and the old handler cannot settle it

  Scenario: A generating project with no active run is adopted
    Given a carousel in a generating phase with no queued or running generation run
    When the owner clicks Reprocessar
    Then an adopt run resumes the current phase without replaying a review decision

  Scenario: Not stuck work is refused with a reason
    Given work waiting for owner review, normally queued, or running with a fresh heartbeat
    When the owner clicks Reprocessar
    Then the response is 409 with a stable reason and no new work

  Scenario: A cross-owner existing run is rejected
    Given an owner supplies another project's active manual run UUID
    When they reprocess their own project
    Then the response is 404 and no audit or maintenance notification is created

  Scenario: Double click returns the existing manual run
    Given two sequential or concurrent Reprocessar clicks for the same stuck work
    When both requests finish
    Then one active generation run and one effective audit event remain
    And the second response names the existing run

  Scenario: Manual recovery is outside cap and backlog and keeps class FIFO
    Given three automatic runs already used the daily cap and ordinary work is queued
    When an owner reprocesses a failed-terminal autopilot run and another manual run
    Then no backlog row or cap increment is created
    And only failed-terminal replacements are excluded from the existing cap count
    And in-place dead-letter and retry-wait recovery leave that count unchanged
    And manual runs go next after the current drive in priority and original job-id order

  Scenario: Process queue now shares maintenance locks with schedules
    Given a scheduled promotion or recovery pass and an owner Processar fila agora request
    When they run concurrently
    Then the shared functions cannot double-promote, double-revive, purge twice, or send duplicate summaries

  Scenario: Full maintenance subsumes queued scheduled passes
    Given a full pass and scheduled promotion or scan jobs are queued
    When the full pass completes successfully
    Then queued scheduled jobs are cancelled without repeated work or another summary
    And run-specific dispatch jobs remain queued
    And scheduled work that sees an active full pass exits without running

  Scenario: Maintenance control jobs are durable and deduped
    Given manual full, scheduled promotion, and scheduled scan requests
    And repeated dispatch requests for one run
    When their control jobs are enqueued
    Then one active job per mode-specific dedupe payload wakes the worker
    And enqueue failure returns false or 503 honestly

  Scenario: Retry and stale transport jobs use explicit fences
    Given a delayed queued retry and a picked job from an old attempt
    When manual recovery kicks them
    Then the queued retry becomes eligible now with priority one
    And the picked job is cancelled and replaced once without preempting its drive

  Scenario: Panel polling and positions stay consistent
    Given unstaged autopilot work, running elapsed time and retry-wait work
    When the board and Telegram compute positions and ETAs
    Then they use the same order and estimate
    And retry-wait never renders #0

  Scenario: Owner cancel does not alarm the owner
    Given Pedro cancels his own queued run
    When the state-change notice is evaluated
    Then no Telegram failure message is sent and the audit event is retained

  Scenario: Recovery failures never expose SQL parameters
    Given a SQLAlchemy error carrying SQL and bound prompt parameters
    When its summary and structured log are rendered
    Then only exception type and safe DBAPI metadata remain
