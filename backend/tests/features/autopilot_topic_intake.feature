Feature: Autopilot topic intake
  The scout posts 1–3 topic proposals. The backend distrusts them: every
  source URL must have been served in the signals bundle within the last
  6 hours, free-text fields cannot carry URLs, and at most
  AUTOPILOT_DAILY_CAP runs are queued per America/Sao_Paulo day.

  Scenario: Best valid topic is queued
    Given the signals bundle served URLs A and B
    When the scout posts topics citing A (score 90) and B (score 70)
    Then both candidates are stored
    And one autopilot run is queued for the score-90 topic

  Scenario: Invented source is rejected
    When the scout posts a topic citing a URL not in the signals bundle
    Then that topic is rejected with reason "source_not_in_signals"

  Scenario: A foreign URL rejects only that proposal
    Given the signals bundle served URL A
    When the scout posts one topic citing a foreign URL and one citing A
    Then only the foreign topic is rejected with reason "source_not_in_signals"
    And the topic citing A is queued

  Scenario: Daily cap
    Given one run was already queued today
    When the scout posts a valid topic
    Then the candidate is stored
    And no run is queued and the reason is "daily_cap_reached"

  Scenario: Replay is idempotent
    Given a batch was already accepted
    When the same batch is posted again
    Then no new run is queued
    And no second candidate is stored

  Scenario: Schema violation persists nothing
    When the scout posts a topic batch that violates the schema
    Then the response status is 422
    And no candidate is stored

  Scenario: URL in free text is rejected
    Given the signals bundle served URL A
    When the scout posts a topic whose brief contains a URL
    Then that topic is rejected with reason "url_in_text"
    And no candidate is stored

  Scenario: Instructions in the brief stay inert text
    Given the signals bundle served URL A
    When the scout posts a topic whose brief tells the model to ignore instructions
    Then the candidate is stored with that brief unchanged
    And one run is queued

  Scenario: Recent carousel topic is a duplicate
    Given a carousel topic created within the last 60 days
    When the scout posts a topic whose title is too similar
    Then that topic is rejected with reason "duplicate_topic"
    And no candidate is stored

  Scenario: Carousel topic older than 60 days is not a duplicate
    Given a carousel with the same topic created more than 60 days ago
    When the scout posts a valid topic with that title
    Then the candidate is stored
    And one run is queued

  Scenario: Control characters are stripped
    Given the signals bundle served URL A
    When the scout posts a title containing a null character
    Then the stored title has no control characters
    And one run is queued

  Scenario: Signal URL older than six hours is rejected
    Given URL A was served more than 6 hours ago
    When the scout posts a topic citing A
    Then that topic is rejected with reason "source_not_in_signals"

  Scenario: Served signals become the allowlist
    Given the scout has just read a signals bundle containing URL A
    When the scout posts a topic citing A
    Then the candidate is stored
    And one run is queued

  Scenario: Daily cap uses America/Sao_Paulo
    Given a run was created before midnight in America/Sao_Paulo
    When the scout posts a valid topic after that midnight
    Then one run is queued

  Scenario: A higher daily cap queues more than one run
    Given AUTOPILOT_DAILY_CAP is 2
    And the signals bundle served URLs A and B
    When the scout posts topics citing A and B
    Then two autopilot runs are queued

  # --- AE-0348 QA round 1 -------------------------------------------------

  Scenario: Concurrent duplicate topic POSTs
    Given two scout POSTs carry the same signal hash at the same time
    When both are accepted
    Then exactly one topic candidate and at most one run exist
    And the losing batch reports the topic as "duplicate_topic"

  Scenario: Over-long URLs are rejected
    Given a topic source or an X observation URL longer than 300 characters
    When it is posted
    Then the request is rejected with 422
