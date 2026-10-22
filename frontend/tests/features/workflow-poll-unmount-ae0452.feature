@AE-0452 @frontend
Feature: The workflow polling fallback stops when the page goes away
  While live updates are down, the workflow workspace polls the workflow state
  with a backoff. Leaving the page must stop that loop, including a poll that
  was still in flight when the page unmounted.

  Scenario: A poll answered after unmount does not schedule another poll
    Given the workflow workspace is on the polling fallback
    And a workflow state poll is in flight
    When the workspace unmounts
    And the poll answers
    Then no further workflow state poll is made

  Scenario: A scheduled poll is cancelled on unmount without live updates support
    Given the browser has no EventSource
    And the workflow workspace is on the polling fallback with a poll scheduled
    When the workspace unmounts
    Then the scheduled poll never runs
