Feature: Daily recovery isolates a failing dead letter
  The daily scan finishes every independent stage when one revive fails. A failed
  attempt rolls back completely so a later scan can use the item's one recovery,
  while concurrent recovery paths cannot complete the same revive twice.

  Scenario: One failing dead letter does not stop the daily scan
    Given several recoverable dead letters and one revive raises "database unavailable"
    When the daily scan runs
    Then the other dead letters are revived
    And old rows are purged and queue counts are collected
    And the owner summary names the failed item and "database unavailable"

  Scenario: A failed revive does not consume the recovery attempt
    Given a recoverable dead letter whose revive raises before commit
    When the daily scan runs
    Then its recovery marker and autopilot state are unchanged
    When the next daily scan succeeds
    Then the item is revived once and its marker is stored

  Scenario: Concurrent recovery and owner retry revive only once
    Given one recoverable dead letter
    When two recovery paths or the scan and Pedro's owner retry race
    Then exactly one path reports a successful revive
    And the generation run is queued once

  Scenario: Each failed recovery is logged without content
    Given a revive raises an exception whose message includes sensitive content
    When the daily scan contains that item failure
    Then one structured log names both run ids and the exception type
    And the log has no payload, prompt, traceback, or exception-message text
