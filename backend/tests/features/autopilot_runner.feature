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

  # QA r3 Q3: the wake check runs before the close, and a fix is never lost.
  Scenario: A fixed escalation is woken, never closed
    Given an escalated run last updated 73 hours ago
    And its carousel is back at final review awaiting a human at a new lock version
    When the runner sweeps escalations
    Then the run is woken to "awaiting_owner"
    And a fixed run outside this sweep's wake scan is not closed either
    And a run whose carousel cannot be read is not closed

  Scenario: A fixed escalation without a notifier is recorded before it closes
    Given no Telegram notifier is configured
    And an escalated run 73 hours old whose carousel was fixed at a new lock version
    When the runner sweeps escalations
    Then the run stays escalated with reason "notifier_unconfigured"
    And it is closed only 72 hours after that record
    And it wakes instead if the notifier is configured in the meantime


  # --- AE-0362 hotfix: the pipeline's real slide count ----------------------

  Scenario: The autopilot creates the project with the pipeline's 7 slides
    Given the autopilot driver creates a carousel project
    Then its slides_config is the pipeline default "1 intro, 1 summary, 3 content, 1 closing, 1 cta"
    And the expected slide count for that project is 7

  Scenario: The contract's slide_count wins over a stale slides_config
    Given a project whose slides_config asks for 6 slides
    And its presentation policy contract has slide_count 7
    Then the expected slide count is 7

  Scenario: A project rewritten to "7_slides" still expects 7 slides
    Given a project whose slides_config is "7_slides"
    Then the expected slide count is 7

  Scenario: An unreadable contract falls back to the project's config
    Given the presentation policy contract cannot be loaded
    And the project's slides_config asks for 6 slides
    Then the expected slide count is 6

  Scenario: Outline and images gates accept the pipeline's 7 slides
    Given a project created by the autopilot driver
    When the outline gate shows 7 outline items
    Then the policy approves the outline gate
    When the images gate shows 7 raw 1536x1024 OpenAI hero JPEGs
    Then the policy approves the images gate

  Scenario: A real slide-count mismatch is still revised
    Given a project created by the autopilot driver
    When the outline gate shows 5 outline items
    Then the outline gate is revised with reason "outline_slide_count_mismatch"
    When the images gate shows 6 images or one image file is missing
    Then the images gate is revised with reason "image_assets_invalid"

  Scenario: The images gate checks the hero images the pipeline stores
    Given the images phase stores one raw hero JPEG per slide in "image_assets"
    And the 1080x1350 slides are only composed later, at finalize
    When every hero image is a present JPEG with a decodable size
    Then the policy approves the images gate
    But a missing file, a non-JPEG, or a zero width or height is revised

  # AE-0363: an autopilot approve recorded the decision but the next phase
  # never ran (prod 2026-10-14, carousel 8e350d6e). The in-tick resume held
  # the lock bump uncommitted, set no run heartbeat, and turned a provider
  # error into a silent "provider_outage" after the checkpointer had already
  # committed the approved gate. The policy then waited forever.

  Scenario: An autopilot approve of the outline runs the content phase
    Given a carousel waiting at the outline gate with a passing outline
    When the runner approves the outline gate
    Then the content phase runs and the workflow waits at the content gate
    And the slide drafts exist and the content gate is not approved
    And the carousel row is at "content" "awaiting_human" with the lock version bumped once
    And the run finished with reason "completed"

  Scenario: The phase runs with a live run and a committed lock bump
    Given a carousel waiting at the outline gate
    When the runner approves the outline gate
    Then while the content phase runs the row is "in_progress" with run_started_at set
    And the heartbeat loop refreshes run_heartbeat_at during the LLM work
    And the worker tick holds no open transaction while the phase runs

  Scenario: A provider error in the next phase escalates, never parks
    Given a carousel waiting at the outline gate
    And the content phase fails with a provider timeout
    When the runner approves the outline gate
    Then the carousel row is marked "failed" and the run finished with reason "failed"
    And the next tick escalates the run with reason "phase_failed"

  Scenario: A freshly parked workflow waits for the grace period
    Given the checkpoint is at "content" "approved" with the content node pending
    And the carousel row is at "outline" "awaiting_human" with no run in flight
    And the row changed less than 600 seconds ago
    Then the gate is parked and the policy waits

  Scenario: A parked workflow past the grace period is re-driven
    Given the checkpoint is at "content" "approved" with the content node pending
    And the carousel row is at "outline" "awaiting_human" with no run in flight
    And the row has not changed for more than 600 seconds
    Then the policy re-drives with reason "engine_parked_no_run_in_flight"
    When the runner re-drives the parked phase
    Then the content node runs again under a live run, with no review decision sent
    And the workflow waits at the content gate for the policy check

  Scenario: A parked workflow that cannot be re-driven escalates
    Given a parked workflow past the grace period whose status is not re-drivable
    Then the policy escalates with reason "engine_parked_no_run_in_flight"
    Given a re-drive finds no parked node
    Then nothing is written and the runner escalates with reason "engine_parked_no_run_in_flight"

  Scenario: A carousel with a run in flight is never resumed twice
    Given the carousel row is "in_progress"
    Then the policy waits even if the checkpoint shows a review gate
    And a resume is refused with "in_progress" before any write

  Scenario: A revise re-runs the phase and a capped revise changes nothing
    Given a carousel waiting at the outline gate
    When the runner revises the outline gate
    Then the outline phase runs again and waits at the outline gate
    Given the outline revision cap is reached
    When the runner revises the outline gate
    Then the resume is refused with "revision_cap" and the row is unchanged

  # AE-0364: the autopilot attaches no persona, so the content phase scores
  # nothing (prod 2026-10-14, carousel 8e350d6e: 7 drafts, persona_scores {}).
  # The engine skips the voice floor when there are no scores; the policy
  # treated "no score" as a failure and revised the content gate to the cap.

  Scenario: A content gate with no persona scores is approved like the engine does
    Given the content gate has drafts and no persona scores
    And no forbidden phrase or engine blocker applies
    When the runner reads the gate
    Then the policy approves the content gate
    And the engine's own content-approve check agrees

  Scenario: The autopilot approves an unscored content gate and the workflow moves to design
    Given a carousel waiting at the content gate with drafts and no persona scores
    When the runner approves the content gate
    Then the design phase runs and the workflow waits at the design gate

  Scenario: Persona scores, when present, still enforce the voice floor
    Given the content gate persona scores have a lowest overall of 62
    Then the policy revises the content gate with reason "persona_score_below_threshold"
    Given the content gate persona scores have a lowest overall of 75
    Then the policy approves the content gate

  Scenario: An unscored run still fails on forbidden phrases and engine blockers
    Given the content gate has no persona scores
    And a draft contains a forbidden phrase
    Then the policy revises the content gate with reason "forbidden_phrase"
    Given the content gate has no persona scores
    And the engine's content-approve check reports a presentation blocker
    Then the policy revises the content gate with reason "presentation_validation_blocked"

  Scenario: An unreadable persona score fails closed
    Given the content gate persona entry is present but not a number
    Then the snapshot counts it as 0 and the policy revises

  Scenario: The owner sees that the run was not scored
    Given a run that reaches final review with no persona scores
    When the review album caption is built
    Then it reads "Persona: not scored"
