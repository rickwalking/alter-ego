Feature: Typed carousel conflict details and serialization lock (AE-0316)
  Carousel 409 responses carry a machine-readable conflict payload alongside
  the legacy detail string, and artifact mutators serialize on a per-project
  session-scoped advisory lock.

  Scenario: Resume during an active run returns a typed conflict
    Given a carousel workflow run is in progress
    When a resume request is submitted
    Then the response status is 409
    And the legacy detail string is preserved for existing clients
    And the conflict payload carries code run_in_progress

  Scenario: Stale lock version returns a distinct typed conflict
    Given a resume request with an outdated lock_version
    When the compare-and-swap fails
    Then the conflict payload carries code version_conflict

  Scenario: Revision cap conflict names the charged phase
    Given a workflow phase whose revision cap is exhausted
    When a revise resume is submitted
    Then the conflict payload carries code revision_cap_exceeded
    And the conflict payload names the charged phase

  Scenario: Resume is refused while an artifact mutator holds the lock
    Given another operation holds the carousel's advisory lock
    When a resume request is submitted
    Then the conflict payload carries code mutation_in_progress
    And after the lock is released the resume succeeds

  Scenario: Advisory lock serializes concurrent holders
    Given one holder inside the carousel project lock
    When a second caller uses the non-blocking variant
    Then it receives a typed mutation_in_progress conflict
    And a blocking second holder acquires the lock only after release

  Scenario: The lock spans sequential transactions by one holder
    Given a holder inside the carousel project lock
    When the holder commits two sequential transactions
    Then the lock remains held until the context exits
