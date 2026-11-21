Feature: The drift reconciler clears a stale content gate (AE-0639)

  Prod carousel 4223b53a: a drift repair converged the checkpoint's presentation
  report to valid but left content_gate_validation blocking on a translation shape
  mismatch the slides no longer had. The autopilot read the stale gate, rewrote
  slide 3 five times for a violation it could not see, and escalated. The owner's
  next Retry of the then-clean gate would have re-drafted the whole deck again.

  Scenario: A stale blocking content gate is converged and cleared
    Given a clean projection
    And a checkpoint whose presentation report passes but whose content gate blocks
    When the drift reconciler runs
    Then it converges the checkpoint
    And the content gate is written empty

  Scenario: A convergence clears the content gate with the presentation report
    Given a clean projection
    And a checkpoint whose presentation report and content gate both block
    When the drift reconciler runs
    Then the presentation report is written non-blocking
    And the content gate is written empty

  Scenario: A system retry of a gate that passes re-drafts nothing
    Given a carousel parked at a content gate that passes
    When the owner retries and the system writes a revise note that names no slide
    Then the revision is a fix and no slide is re-drafted

  Scenario: A system note that names a slide keeps its scoped rework
    Given a carousel parked at a content gate that passes
    When the autopilot sends the revise note "Slide 6 (pt body): body_too_long"
    Then the revision is a rework of the named slide

  Scenario: An autopilot persona revise of a passing gate keeps its rework
    Given a carousel parked at a content gate that passes
    When the autopilot sends a persona_score_below_threshold revise note
    Then the revision is a rework
