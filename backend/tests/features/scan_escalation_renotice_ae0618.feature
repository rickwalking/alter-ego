Feature: The daily recovery scan re-sends the escalation notice with Retry once to stuck runs (AE-0618)
  Pedro's decision (2026-11-04): the daily clean-up routine gives failed or escalated
  runs that are still unresolved another chance to be retried, by re-sending the
  escalation notice that carries the owner's Retry button (AE-0606). A run gets this
  at most once. The scan only emits an outbox event; the worker's notifier sends it.

  Background:
    Given the owner's carousel Retry shipped on 2026-11-04

  Scenario: An eligible escalated run gets one notice with the carousel Retry
    Given a run escalated before Retry shipped whose carousel waits at a gate
    When the daily scan runs
    And the worker's notifier ticks
    Then the outbox holds exactly one escalation_renotice event for the run
    And the notifier sends one escalation notice with the carousel Retry keyboard
    And the run's notice ledger holds the re-notify marker and the delivered event id

  Scenario: A failed run with a live carousel gets the same notice
    Given a run that failed before Retry shipped whose carousel phase failed
    When the daily scan runs
    And the worker's notifier ticks
    Then the notifier sends one escalation notice with the carousel Retry keyboard

  Scenario: A second scan sends nothing
    Given a run the scan already re-notified
    And the notice was delivered
    When the daily scan runs again
    Then no new event is written for the run

  Scenario: A notice still waiting in the outbox is not emitted again
    Given a run the scan already re-notified
    And the worker's notifier has not ticked
    When the daily scan runs again
    Then no new event is written for the run

  Scenario: A notice the notifier gave up on is not offered again
    Given a run the scan already re-notified
    And every delivery attempt failed
    When the daily scan runs again
    Then no new event is written for the run

  Scenario Outline: A settled or running carousel is skipped
    Given a run escalated before Retry shipped whose carousel is <carousel>
    When the daily scan runs
    Then no event is written for the run
    And the run carries no re-notify marker

    Examples:
      | carousel                    |
      | rejected                    |
      | approved at its phase       |
      | approved for publish        |
      | published                   |
      | archived                    |
      | running                     |

  Scenario: A failed run with an auto-rejected carousel is skipped
    Given a run that failed before Retry shipped whose carousel was auto-rejected
    When the daily scan runs
    Then no event is written for the run

  Scenario: A running carousel is picked up once it stops
    Given a run escalated before Retry shipped whose carousel is running
    And the daily scan skipped it
    When the carousel stops at a gate
    And the daily scan runs again
    Then the outbox holds exactly one escalation_renotice event for the run

  Scenario: A run already notified with Retry is skipped
    Given a run escalated after Retry shipped
    When the daily scan runs
    Then no event is written for the run

  Scenario: An escalation not delivered yet still counts as notified
    Given a run escalated after Retry shipped whose notice is still in the outbox
    When the daily scan runs
    Then no event is written for the run

  Scenario Outline: A run closed by the owner or by a retry is skipped
    Given a failed run with reason <reason> and a live carousel
    When the daily scan runs
    Then no event is written for the run

    Examples:
      | reason                |
      | owner_queue_cancelled |
      | owner_queue_discard   |
      | owner_queue_retry     |
      | queue_daily_recovery  |

  Scenario: A run with no carousel is skipped
    Given a failed run that never got a carousel
    When the daily scan runs
    Then no event is written for the run

  Scenario: A run in any other state is skipped
    Given a run awaiting the owner with a live carousel
    When the daily scan runs
    Then no event is written for the run

  Scenario: A run the queue parked keeps its own buttons
    Given a run parked by the queue before Retry shipped with a live carousel
    When the daily scan runs
    And the worker's notifier ticks
    Then the notifier sends the parked notice with "Tentar de novo" and "Descartar"

  Scenario: A failing item does not stop the others
    Given three eligible runs
    And re-notifying the second one fails
    When the daily scan runs
    Then the first and the third are re-notified
    And the failure is logged with exception metadata only
    And the summary names the failed run

  Scenario: A failed item writes nothing and stays eligible
    Given an eligible run
    And the database fails while its event is staged
    When the daily scan runs
    Then neither the event nor the marker is stored
    And the next scan re-notifies it

  Scenario: A failing listing does not stop the scan
    Given the listing of stuck runs fails
    When the daily scan runs
    Then the purge still runs
    And the summary reports the failure

  Scenario: The summary carries the count
    Given two eligible runs
    When the daily scan runs
    Then the summary Pedro receives says 2 runs were re-notified

  Scenario: A quiet day's summary does not change
    Given no eligible run
    When the daily scan runs
    Then the summary is the one Pedro received before this step existed

  Scenario: Nothing else changes
    Given an eligible run
    When the daily scan runs
    Then the run's state, reason, updated_at and lock fields are unchanged
    And the carousel row is unchanged

  Scenario: Concurrent scans emit one event
    Given an eligible run
    When two daily scans run at the same time
    Then the outbox holds exactly one escalation_renotice event for the run

  Scenario: A run that moved on after the listing is left alone
    Given an eligible run that the owner retried after the listing
    When the scan tries to re-notify it
    Then no event is written and the run is not counted

  Scenario: With autopilot driving off the step does nothing
    Given autopilot driving is off
    When the daily scan runs
    Then no run is re-notified
