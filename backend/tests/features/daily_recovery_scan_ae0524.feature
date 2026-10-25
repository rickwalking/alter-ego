Feature: A daily recovery scan puts stuck carousel work back in the queue (AE-0524)
  Once a day at 04:00 São Paulo time the generation worker retries, once, the
  autopilot runs the queue parked for a transient-class reason, resumes autopilot
  runs a dead driver left stale, lists the dashboard projects nobody is driving,
  purges old queue rows and sends Pedro one summary. PgQueuer's schedule table
  makes it run once a day across workers and restarts.

  Scenario: The daily scan is scheduled at 04:00 São Paulo time
    Given the generation worker starts
    Then the scan is registered on PgQueuer's scheduler as "0 7 * * *" (UTC)

  Scenario: A recent transient dead letter is retried once
    Given an autopilot drive the queue parked yesterday after its retries ran out
    When the scan runs
    Then the dead letter is marked tried and its autopilot run is put back in the queue

  Scenario: A second scan the same day retries nothing again
    Given the scan already retried a dead letter
    When the scan runs again
    Then that dead letter is not retried a second time

  Scenario: A theme the scan already retried is not retried again
    Given the scan queued a new run for a theme whose run failed before it started
    When that new run is dead-lettered too and the scan runs again
    Then no third run is queued for the theme

  Scenario: A stale run is resumed only once, and not in its first hour
    Given a run the scan resumed that went stale again, and a run escalated 20 minutes ago
    When the scan runs
    Then neither is resumed

  Scenario: A dead letter Pedro already resolved is not retried
    Given a dead letter whose autopilot run Pedro discarded on Telegram
    When the scan runs
    Then the run stays discarded and the dead letter is marked tried

  Scenario: A permanent or old dead letter is left alone
    Given a dead letter with a permanent error and one parked eight days ago
    When the scan runs
    Then neither is retried

  Scenario: A stale autopilot escalation resumes from its checkpoint
    Given an autopilot run escalated as stale yesterday
    When the scan runs
    Then the run is generating again and the dispatcher stages its drive

  Scenario: Parked dashboard projects are listed, not resumed
    Given a dashboard project left in progress with nothing queued
    When the scan runs
    Then the summary names it and nothing is queued for it

  Scenario: Old succeeded runs and PgQueuer logs are purged
    Given succeeded runs older than 30 days and a recent one
    When the scan runs
    Then only the old ones are deleted

  Scenario: Pedro receives one summary
    When the scan finishes
    Then one message gives the recovered, still dead and queued counts

  Scenario: A failed scan is logged and tried again the next day
    Given the scan fails
    Then no summary is sent and the worker keeps running
