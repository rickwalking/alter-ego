Feature: A failed carousel phase terminates the run and stays retryable (AE-0330)
  The content node returns early on phase_status=failed without opening a
  review gate. The gate router only knew "approved" and "retry", so a failed
  phase was routed straight back into itself: ~10,000 steps at four per
  second with no LLM call, until langgraph's 10007-step recursion limit —
  14 minutes and ~350k checkpoint rows per failure, observed live 2026-09-14.
  It struck the same project twice: once on a real draft failure, then again
  with every draft already built, because resume only flips the DB row to
  in_progress and never clears the stale failed flag in the checkpoint.

  Scenario: a failed phase leaves the graph instead of retrying itself
    Given a phase whose artifacts failed this run
    When the gate router evaluates the phase
    Then it routes to the failed edge
    And the failed edge is wired to END on every gated phase

  Scenario: a fresh artifact failure does not open a review gate
    Given the content artifact runner reports a failure
    When the content node runs
    Then it returns the failed status without calling interrupt

  Scenario: a stale failed flag does not block a successful rebuild
    Given the checkpoint still carries failed from a previous run
    And the content artifacts are rebuilt successfully this run
    When the content node runs
    Then the stale failed status and error are cleared
    And the review gate opens as normal

  Scenario: a retry re-enters a failed phase parked at END
    Given a run that ended with a failed content phase
    When the reviewer retries
    Then the engine reopens the graph at the content phase
    And the rebuilt drafts advance to the design gate

  Scenario: the graph runs under an explicit recursion limit
    Given the carousel run configuration
    Then it carries a recursion limit far below langgraph's 10007 default
    And any future self-routing loop fails in seconds, not minutes
