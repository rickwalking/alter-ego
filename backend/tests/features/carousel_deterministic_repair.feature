Feature: One-click deterministic carousel repair
  As a carousel creator hitting blocking presentation violations,
  I want a single authenticated action that runs the deterministic repairs,
  So that I can self-serve instead of needing operator SSH surgery.

  Background:
    Given the deterministic repair pipeline (scaffold strip, heading-echo
      removal, body trim to policy budget, canonical shape normalization,
      and policy-gated casing) is available server-side

  Scenario: User repairs a scaffold-contaminated slide from the UI
    Given a carousel whose slide 4 body contains the raw drafting scaffold
    And the design step shows blocking presentation violations
    When the user clicks "Fix issues automatically"
    Then the repair endpoint strips the scaffold and trims the body
    And the checkpoint state and the slides projection both hold the repair
    And the fresh validation report is returned in the response
    And the violation panel clears after state refresh

  Scenario: Repair loses the race against a concurrent resume
    Given a repair request has passed the in-progress check
    And a resume request bumped the lock version before the repair mutates
    When the repair attempts its compare-and-swap
    Then the repair fails with 409 version_conflict and mutates nothing

  Scenario: Repair is refused while a revision run is active
    Given the carousel workflow phase status is in_progress
    When the user clicks "Fix issues automatically"
    Then the endpoint responds 409 with a run-in-progress detail
    And the UI shows the revision-in-progress state instead of a toast

  Scenario: Repair and republish serialize on the shared advisory lock
    Given a completed carousel already holds the per-project advisory lock
    When a repair is submitted for the same carousel
    Then the repair fails with 409 mutation_in_progress and mutates nothing

  Scenario: A second repair on already-clean content is a no-op
    Given a carousel whose slides are already clean
    When the repair endpoint runs
    Then the response status is a no-op and no store is mutated

  Scenario: Unrepairable violations are reported honestly
    Given a slide whose violation cannot be fixed deterministically
    When the repair endpoint runs
    Then repairable violations are fixed and the rest are returned
    And the validation report reflects only the remaining violations

  Scenario: A completed carousel chains repair into a republish
    Given a completed carousel with a scaffold-contaminated persisted slide
    When the repair endpoint runs
    Then the persisted slide projection is fixed
    And the response signals that a republish is needed to refresh the PDF

  Scenario: A partial failure is auto-converged by the watchdog tick
    Given a repair committed the projection but died before the checkpoint write
    When the workflow-workers tick runs after the reaper
    Then the drift reconciler converges the stale checkpoint from the projection
    And it emits carousel_repair_drift_detected and _converged events
    And it required no client retry

  Scenario: A v2-stamped project fires casing rules at the content gate
    Given a new project stamped with the v2 presentation policy version
    When the content-phase validation runs
    Then the policy version is threaded into the validation command
    And casing warnings are produced for lowercase headings and proper nouns
    And a legacy NULL/v1 project keeps its v1 semantics
