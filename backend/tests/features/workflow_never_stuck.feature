Feature: Never-stuck workflows (AE-0210, AE-0212)
  CLAUDE.md mandates "Auto-reject after timeout; never leave workflows stuck."
  The workflow worker must transition timed-out workflows to a terminal rejected
  state, and must log a traceback when a worker tick fails.

  Background:
    Given the workflow worker runs periodically

  Scenario: Workflow past the timeout is auto-rejected
    Given a carousel workflow stuck at brief/pending updated beyond the timeout
    When the worker auto-reject step runs one tick
    Then the workflow phase_status is rejected
    And the workflow status is failed
    And a phase-changed event is emitted

  Scenario: Workflow within the timeout window is left untouched
    Given a carousel workflow at brief/pending updated within the timeout window
    When the worker auto-reject step runs one tick
    Then the workflow phase_status remains pending

  Scenario: In-progress workflow is not auto-rejected
    Given a carousel workflow whose phase_status is in_progress beyond the timeout
    When the worker auto-reject step runs one tick
    Then the workflow phase_status remains in_progress

  Scenario: Worker tick failure renders a traceback
    Given a worker dependency raises an exception during a tick
    When the worker loop handles the error
    Then the workflow_workers_error log event includes a traceback
