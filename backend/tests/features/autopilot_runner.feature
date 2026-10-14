Feature: Autopilot runner
  As the in-process autopilot runner
  I want to drive a queued carousel through the editorial gates
  So that the owner is asked only at final review

  Scenario: Clean run reaches the owner
    Given a queued autopilot run
    And every gate's policy check passes
    When the runner ticks until idle
    Then the run state is "awaiting_owner"
    And final_review was never approved by the runner
    And one "content.autopilot.ready_for_owner" event was emitted

  Scenario: Low persona score is revised then escalated
    Given the content gate persona score stays at 62
    When the runner ticks until idle
    Then the content gate was revised 2 times
    And the run state is "escalated" with reason "persona_score_below_threshold"

  Scenario: Version conflict is retried safely
    Given the resume call returns a lock_version conflict
    When the runner ticks twice
    Then exactly one approve is applied to that gate

  Scenario: Provider outage on start
    Given workflow start fails with 503 three times
    When the runner ticks three times
    Then the run state is "failed" with reason "start_failed"

  Scenario: Disabled worker skips the runner
    Given autopilot is disabled
    When the worker tick runs
    Then the runner is not called

  # --- AE-0348 QA round 1 -------------------------------------------------

  Scenario: The engine rejects an approve the policy allowed
    Given the content gate persona entry has no "overall" score
    And the engine reads a missing "overall" as 0
    When the runner reads the gate
    Then the policy revises instead of approving
    And no approve is sent that the engine would refuse

  Scenario: Content approve with blocking presentation violations is revised
    Given the content gate passes persona and forbidden-phrase checks
    And the engine's own content-approve check reports a presentation blocker
    When the runner ticks
    Then the content gate is revised with reason "presentation_validation_blocked"

  Scenario: Design is revised at most once
    Given the design gate still has presentation blockers after one revise
    When the runner ticks
    Then the run state is "escalated" with reason "presentation_validation_blocked"

  Scenario: An unclassified engine error escalates the run instead of looping
    Given a generating run whose resume raises an unclassified ValueError
    When the runner ticks
    Then the session is rolled back
    And the run state is "escalated" with a reason starting "engine_error:ValueError"
    And the next tick does not retry that run

  Scenario: An unclassified start error fails the queued run
    Given a queued run whose workflow start raises an unclassified error
    When the runner ticks
    Then the run state is "failed" with a reason starting "engine_error"

  Scenario: An autopilot failure does not roll back the other worker steps
    Given the stale-run reaper and the auto-reject made changes this tick
    And the autopilot runner step raises
    When the worker tick runs
    Then the reaper and auto-reject changes are committed
    And only the autopilot step is rolled back
    And the Telegram step still runs

  Scenario: 72 hour expiry
    Given a run in "awaiting_owner" whose last transition was 72 hours ago
    When the runner ticks
    Then the run state is "expired" with reason "owner_review_expired"
    And the owner is told on Telegram that the review expired

  Scenario: An escalated run the owner fixed in the web UI returns to the owner
    Given an escalated run recorded at lock version 4
    And its carousel is back at final review awaiting human at lock version 6
    When the runner ticks
    Then the run state is "awaiting_owner"
    And one "content.autopilot.ready_for_owner" event was emitted for revision 6

  Scenario: An escalated run whose carousel did not change stays escalated
    Given an escalated run recorded at lock version 4
    And its carousel is at final review awaiting human at lock version 4
    When the runner ticks
    Then the run state stays "escalated"

  Scenario: The autopilot imports editorial code only through its facade
    Given the import-linter contract "autopilot-editorial-facade-only"
    When a module under the autopilot imports the legacy carousel service, the carousel ORM, or an editorial internal
    Then lint-imports fails on that contract

  # QA r2 R1: escalations neither starve each other nor stay open forever.
  Scenario: A fixed escalation wakes even behind five abandoned ones
    Given five escalated runs nobody has touched
    And a newer escalated run whose carousel is back at final review at a new version
    When the runner sweeps twice
    Then the newer run is back in "awaiting_owner" with reason "owner_fixed_in_web_ui"
    And checking a run never moves its "updated_at"

  Scenario: An escalation nobody fixes is closed after 72 hours
    Given a run "escalated" 73 hours ago
    When the runner sweeps
    Then the run is "rejected" with reason "escalation_expired"
    And the owner is told on Telegram that the escalation was closed

  Scenario: An escalation whose carousel was rejected is closed
    Given an escalated run whose carousel the owner rejected in the web UI
    When the runner sweeps, with or without Telegram configured
    Then the run is "rejected" with reason "carousel_rejected"
    And the owner is told on Telegram that the escalation was closed
