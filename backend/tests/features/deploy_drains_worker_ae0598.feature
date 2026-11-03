Feature: A deploy drains the generation worker before it stops it
  Pedro's decision (2026-11-02): before the deploy stops the generation worker it
  pauses new job pickup and lets the current job reach its next phase boundary,
  so a deploy does not kill an in-flight autopilot run. The wait is bounded; when
  it runs out the worker is stopped as before and the run resumes from its last
  checkpoint on the next worker.

  Scenario: A drained worker refuses to claim a job and puts it back
    Given the drain flag is set and fresh
    When the worker picks a generation job
    Then the job is not claimed, the run is not touched and the job comes back after the drain delay

  Scenario: The worker claims jobs again once the drain is cleared
    Given a drained worker refused a job
    When the drain flag is cleared
    Then the next pick of that job is claimed and handled

  Scenario: A drive in flight yields at the next phase boundary when the worker is drained
    Given an autopilot drive is running a phase
    When the drain flag is set
    Then the drive yields when the phase ends and the worker reports it is idle

  Scenario: The worker reports busy while a job is in flight
    Given the worker is handling a generation job
    When the deploy asks whether the worker is idle
    Then the answer is busy until the job returns, also when the job fails

  Scenario: A stale drain flag no longer pauses the worker
    Given the drain flag is older than the drain time-to-live
    When the worker picks a generation job
    Then the job is claimed and handled

  Scenario: The worker clears the drain flag when it starts
    Given a drain flag and a busy marker left from an earlier deploy
    When the worker starts
    Then both are removed and the worker claims jobs

  Scenario: The deploy waits until the worker is idle, then stops it
    Given the worker is busy for two polls
    When the deploy drain step runs
    Then it sets the drain flag, polls until the worker is idle and exits 0 without waiting the full bound

  Scenario: The deploy drain wait is bounded
    Given the worker stays busy
    When the deploy drain step runs with a bound
    Then it gives up after the bound with a warning and exits 0, so the stop and the checks still run

  Scenario: The deploy skips the drain when the worker is not running
    Given no generation worker container is running
    When the deploy drain step runs
    Then it asks the worker nothing and exits 0

  Scenario: A drain request the worker cannot answer never blocks the deploy
    Given the worker cannot set the drain flag
    When the deploy drain step runs
    Then it warns and exits 0 without polling

  Scenario: The deploy clears the drain flag on the new worker
    Given the stack is back up
    When the deploy clear step runs
    Then the worker is asked to clear the drain flag and a failure only warns

  Scenario: The deploy drains, stops with a short grace and keeps every check
    Given the deploy workflow
    Then the drain step runs after the build and before the worker stop and the stack down
    And the worker stop grace plus the drain bound stays at the old 300 s
    And the pre-start one-shots, the post-start retries, the drift check and the health block still run
    And the ssh command timeout is 15 minutes

  Scenario: The OpenCode sidecar stops on SIGTERM
    Given the production compose file
    Then the opencode service runs under an init process, so SIGTERM reaches opencode as a normal child
