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

  Scenario: Double click returns the existing manual run
    Given two sequential or concurrent Reprocessar clicks for the same stuck work
    When both requests finish
    Then one active generation run and one effective audit event remain
    And the second response names the existing run

  Scenario: Manual recovery is outside cap and backlog and keeps class FIFO
    Given three automatic runs already used the daily cap and ordinary work is queued
    When an owner reprocesses a failed-terminal autopilot run and another manual run
    Then no backlog row or cap increment is created
    And manual runs go next after the current drive in click order

  Scenario: Process queue now shares maintenance locks with schedules
    Given a scheduled promotion or recovery pass and an owner Processar fila agora request
    When they run concurrently
    Then the shared functions cannot double-promote, double-revive, purge twice, or send duplicate summaries

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
