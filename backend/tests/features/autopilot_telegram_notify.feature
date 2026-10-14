Feature: Telegram review notification
  As the autopilot worker
  I want the owner told on Telegram when a run needs them
  So that approval happens from the phone and a replay does not double-send

  Scenario: Owner receives slides and buttons
    Given an autopilot run became ready for the owner with 7 slides
    When the notifier handles the event
    Then Telegram receives one media group with 7 photos
    And one message with Approve, Rework and Reject buttons

  Scenario: Duplicate event is ignored
    Given the review was already sent for this revision
    When the same event is handled again
    Then Telegram is not called

  Scenario: Rate limited
    Given Telegram answers 429 with retry_after 3
    When the notifier sends the review
    Then it retries after 3 seconds and succeeds

  Scenario: Awaiting owner is reminded once
    Given a run has been awaiting the owner for more than 24 hours
    When the reminder sweep runs twice
    Then Telegram receives exactly one reminder

  Scenario: Missing bot token escalates and does not call Telegram
    Given the bot token is unset
    When a run reaches final review
    Then the run is escalated with reason notifier_unconfigured
    And Telegram is not called

  Scenario: Escalated run includes the reason and a link
    Given a run escalated because the persona score stayed low
    When the notifier handles the event
    Then Telegram receives the reason and a web UI link

  Scenario: Published run includes the permalink
    Given a run was published
    When the notifier handles the event
    Then Telegram receives the permalink

  Scenario: Publish failure offers retry
    Given publishing failed after the retries
    When the notifier handles the event
    Then Telegram receives a Retry button

  # --- AE-0348 QA round 1 -------------------------------------------------

  Scenario: Undelivered notices are processed oldest first and never skipped
    Given more than 100 newer autopilot outbox rows than an undelivered notice
    When the notifier ticks repeatedly
    Then the older notice is delivered
    And the cursor never moves past a notice that is still being retried

  Scenario: Review reopened without regeneration sends the keyboard again
    Given a run returned to "awaiting_owner" with reason "owner_rework_not_applied"
    When the notifier ticks
    Then a status message with Approve, Rework and Reject buttons is sent

  Scenario: Expired review notice
    Given a run moved to "expired"
    When the notifier ticks
    Then the owner is told the review expired after 72 hours
