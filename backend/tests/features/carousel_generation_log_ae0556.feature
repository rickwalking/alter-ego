Feature: Carousel generation log
  Queued carousel work records a bounded diagnostic timeline that an owner or
  admin can inspect without Langfuse or exposure of generation content.

  Scenario: A queued carousel has a complete generation timeline
    Given a carousel with queued generation work
    When queue runs, phase attempts, image jobs and export complete
    Then the generation log shows runs newest first with kind, timestamps, attempts and status
    And phases have outcomes and durations
    And image jobs and the final generation status are visible

  Scenario: A failed and retried run exposes safe failure and retry history
    Given a generation run fails transiently and is retried
    When the owner opens the generation log
    Then the failed event has a classified error code
    And the retry and any recovery or manual reprocessing events are visible
    And no raw exception message is exposed

  Scenario: Generation log access is owner and admin only
    Given a carousel with generation events and users with different roles
    When the owner or admin requests the log
    Then the API returns the timeline
    When another editor or an assigned reviewer requests it
    Then the API returns 403 and no cross-project event is returned
    And anonymous requests return 401 and an unknown carousel returns 404

  Scenario: Stored events exclude sensitive failure content
    Given an exception containing a planted secret and a DBAPIError with SQL and bound parameters
    When failure events are recorded with oversized and unknown details
    Then stored rows and API responses contain only classified safe metadata
    And the secret, prompt text, SQL and parameters are absent
    And serialized event details do not exceed 4096 bytes

  Scenario: Event storage failures never break generation
    Given an event store that raises or exceeds its write timeout
    When a generation run succeeds
    Then the generation outcome remains successful
    And one safe warning names only event and exception types
    And recorder latency remains bounded

  Scenario: Waiting autopilot work does not flood the generation log
    Given an autopilot run repeatedly has no work or cannot take its drive lock
    When several queue attempts finish in the same waiting streak
    Then only the first wait records a waiting event and no phase events
    And resumed real work records one run start that closes the wait streak

  Scenario: Generation log pages are stable during new events
    Given more than 200 generation events for one carousel
    When the owner loads bounded pages while a newer event arrives
    Then no event is duplicated or skipped by the keyset cursor
    And each page contains at most 200 events

  Scenario: Daily purge expires generation events after thirty days
    Given events older and newer than thirty days on succeeded runs
    When the existing daily recovery purge runs
    Then only expired events are removed in bounded delete batches
    And run and PgQueuer log purges still complete

  Scenario: Langfuse trace links are optional
    Given Langfuse is disabled or unavailable
    When generation events are recorded
    Then generation and the generation log still work without a trace link
    When a real phase trace exists
    Then its trace id and SDK-generated URL are available to the owner
