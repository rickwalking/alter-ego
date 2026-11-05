Feature: A final-review refresh runs ahead of queued full drives (AE-0617)
  A reworking run whose only remaining work is the final-review stop needs seconds
  of the single generation worker, but it used to wait FIFO behind every full drive
  of 30-35 minutes. Its drive now runs next, at the manual reprocess priority,
  without pre-empting the drive that is running. Every other drive keeps FIFO.

  Scenario: A refresh drive is picked before older ordinary drives
    Given two full drives queued at ordinary priority
    And a reworking run whose carousel waits in final review with no rework queued
    When the dispatcher runs and the worker picks the next job
    Then the refresh drive is picked first
    And the older drives follow in their FIFO order

  Scenario: A drive staged before the run became a refresh is raised
    Given a full drive queued ahead of a drive staged during a website cover hold
    When the hold is released and the dispatcher runs
    Then the second drive keeps its job and is picked first
    And a second dispatcher pass changes nothing

  Scenario: A raised drive waiting for its render keeps its delay
    Given a refresh drive that went back to wait for a render, due in one minute
    When the dispatcher raises it
    Then its job has the raised priority and is not due any sooner

  Scenario: A drive put back to wait is raised on the pass after its retry
    Given the running drive of a refresh run was put back to wait
    And its job is still held by the worker
    When the dispatcher runs and the worker then releases the job for its retry
    Then the job stays as it was until the release
    And the next dispatcher pass raises it and keeps its delay

  Scenario: A running drive is not interrupted
    Given a full drive running on the worker and a refresh drive queued
    When the dispatcher runs
    Then the running drive and its job are unchanged
    And the refresh drive is the next one picked

  Scenario: A refresh drive that is itself running is left alone
    Given the drive of a refresh run is running
    When the dispatcher runs
    Then its stored run and its job are unchanged

  Scenario: A refresh drive with no job yet carries the raised priority
    Given a drive staged at ordinary priority and not handed over yet
    When the run is a refresh at the next dispatcher pass
    Then the job is created at the raised priority

  Scenario Outline: A rework with work left keeps FIFO
    Given a reworking run <situation>
    When the dispatcher runs
    Then its drive stays at ordinary priority

    Examples:
      | situation                                       |
      | with a content revise queued                    |
      | with a "Fix issues" queued                      |
      | with a GrokBot cover queued                     |
      | held by a website cover switch                  |
      | whose revise is regenerating an earlier phase   |
      | whose carousel was approved on the website      |
      | whose carousel was released                     |

  Scenario: Older reworks with work left do not hide a refresh
    Given more older reworking runs than the batch size, none of them a refresh
    And a newer reworking run that only owes the final-review refresh
    When the dispatcher lists the refresh runs
    Then the newer run is listed

  Scenario: A run in another state is no refresh
    Given a run queued, generating or waiting for the owner, at any carousel state
    When the dispatcher lists the refresh runs
    Then the run is not listed

  Scenario: With autopilot off nothing is raised
    Given a worker with autopilot disabled
    When the dispatcher runs
    Then no drive is staged or raised
