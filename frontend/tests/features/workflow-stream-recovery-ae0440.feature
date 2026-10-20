@ae-0440 @editorial-workflow @sse
Feature: The editor's live workflow stream recovers, or says it cannot
  As the owner reviewing a carousel in /dashboard/create/<id>
  I want the live updates stream to notice an expired session, back off when the
  backend is unreachable, and tell me when live updates stopped
  So that the page never sits on stale state while it retries a dead stream forever

  Background:
    Given the owner has a carousel workflow open in the create workspace
    And the workflow stream is connected

  # Happy path
  Scenario: A dropped stream refetches the state and reconnects
    When the workflow stream errors
    And the workflow state probe answers 200 with the current state
    Then the page shows the probed state
    And the stream reconnects after the first backoff delay
    And the reconnected stream refetches the workflow state when it opens

  Scenario: Reconnect delays walk the whole backoff array
    Given the workflow state probe keeps failing with a network error
    When the workflow stream errors repeatedly
    Then each reconnect waits for the next delay of the backoff array
    And the last delay is reused once the array is exhausted

  Scenario: A successful reconnect resets the attempt budget
    Given the stream reconnected after two failed attempts
    When the stream opens
    And the stream errors again later
    Then the next reconnect waits for the first backoff delay again

  # Failure: expired session (the prod incident)
  Scenario: An expired session goes to the session-expired login and stops reconnecting
    When the workflow stream errors
    And the workflow state probe answers 401
    Then the browser goes to the logout route with the current page as redirect
    And the stream is not reconnected
    And no further workflow state poll is scheduled

  Scenario: A forbidden probe stops reconnecting
    When the workflow stream errors
    And the workflow state probe answers 403
    Then the stream is not reconnected

  Scenario: A workflow that no longer exists stops reconnecting
    When the workflow stream errors
    And the workflow state probe answers 404
    Then the stream is not reconnected
    And the page shows that live updates are disconnected

  # Edge: retries exhausted
  Scenario: Live updates disconnect after the reconnect budget is spent
    Given the workflow state probe keeps failing with a network error
    When the workflow stream has errored more times than the reconnect budget
    Then the stream is not reconnected again
    And the page shows "live updates disconnected" with a retry button

  Scenario: Retry reconnects a disconnected stream
    Given live updates are disconnected
    When the owner presses retry
    Then the stream opens again with a fresh attempt budget

  # Edge: tab visibility
  Scenario: Returning to the tab refetches the state and revives a dead stream
    Given live updates are disconnected
    When the owner returns to the tab
    Then the workflow state is probed
    And the stream reconnects

  Scenario: Returning to the tab with a live stream only refetches the state
    When the owner returns to the tab
    Then the workflow state is refetched
    And the open stream is kept

  Scenario: Awaiting review state is refreshed even though polling is off
    Given the workflow is awaiting the owner's review
    When the workflow stream errors
    And the workflow state probe answers 200 with the current state
    Then the page shows the probed state

  # Stale phase progress (contributor to "stuck on image generation")
  Scenario: Image progress of a past phase is not shown as live work
    Given the workflow is running the content phase after a send-back from final review
    And the saved phase progress still describes the image generation phase
    Then the image generation progress is not shown

  Scenario: Image progress is shown while the images phase runs
    Given the workflow is running the images phase
    And the phase progress describes the image generation phase
    Then the image generation progress is shown

  Scenario: Progress without a phase tag is shown for the running phase
    Given the workflow is running a phase
    And the phase progress has a label but no phase tag
    Then the progress is shown
