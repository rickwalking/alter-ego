Feature: Owner actions via Telegram
  As Pedro
  I want Approve, Rework, Reject, and Retry to run exactly once
  So that only I can publish, and a double tap cannot double-post

  Scenario: Approve publishes once
    Given a run awaiting the owner
    When the owner taps Approve twice
    Then final_review is approved once
    And one Instagram publish job is enqueued

  Scenario: Forged request
    When a webhook call arrives without the secret token header
    Then the response status is 401
    And no run changes state

  Scenario: Wrong secret is rejected
    When a webhook call arrives with the wrong secret token header
    Then the response status is 401
    And no run changes state

  Scenario: Stranger presses a button
    Given a callback from a user who is not the owner
    When the webhook handles it
    Then no run changes state

  Scenario: Rework with feedback
    Given a run awaiting the owner
    When the owner taps Rework, chooses Images and replies "darker palette, no robots"
    Then the images phase is revised with that feedback
    And the run returns to awaiting the owner after regeneration

  Scenario: Reject
    When the owner taps Reject
    Then the run is "rejected" and the carousel stays private

  Scenario: Already handled
    Given a run that is not awaiting the owner
    When the owner taps Approve
    Then the owner sees "already handled"
    And no run changes state

  Scenario: Duplicate delivery
    Given the owner already approved from this update
    When Telegram delivers the same update again
    Then final_review is not approved again

  Scenario: Unknown action
    When the owner taps a button whose callback data is not a known action
    Then the owner sees "unknown action"
    And no run changes state

  Scenario: Retry enqueues once
    Given a run whose publish failed
    When the owner taps Retry twice
    Then one Instagram publish job is enqueued

  Scenario: Revision cap escalates
    Given a run awaiting the owner
    When the owner sends rework feedback and the revision cap is hit
    Then the run is "escalated"

  # --- AE-0348 QA round 1 -------------------------------------------------

  Scenario: Rework never runs LLM regeneration inside the webhook
    Given the owner chose the "Images" phase and sent feedback text
    When the webhook handles the text
    Then the run moves to "reworking" with the phase and feedback queued
    And no editorial resume is called during the webhook request
    When the worker runner ticks
    Then the revise is applied once with the owner's feedback and target phase

  Scenario: Rework that cannot be applied reopens the review
    Given a queued rework whose revise hits a provider outage
    When the worker runner ticks
    Then the run returns to "awaiting_owner" with reason "owner_rework_not_applied"
    And the review keyboard is sent again

  Scenario: The editorial approve refuses the owner's Approve
    Given the run is awaiting the owner
    And the editorial approve returns a version conflict
    When the owner taps Approve
    Then the run returns to "awaiting_owner" with reason "owner_approve_refused"
    And the keyboard message keeps the Approve, Rework and Reject buttons

  Scenario: Webhook failure after Telegram side effects
    Given the handler queued a callback answer and an edit
    When the handler fails before the commit
    Then the update claim and every transition are rolled back
    And no Telegram reply is sent
