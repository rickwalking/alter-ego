Feature: Edit carousel text without regenerating images
  As a reviewer or creator
  I want to fix slide text at any review step or after completion
  So that typos and casing issues never require operator access or image regen

  # Backend feasibility + service coverage:
  #   tests/integration/test_carousel_approved_hold_edit.py
  #   tests/unit/application/test_carousel_slide_edit_service.py
  #   tests/unit/api/test_slide_edit_route.py
  #   tests/unit/infrastructure/test_carousel_republish_sweeper.py
  #   tests/unit/api/test_editorial_workflow_routes_sanitize.py

  Scenario: Fix a typo at the final review step
    Given a workflow awaiting human review at final_review
    When the user edits slide 1's heading in the inline editor and saves
    Then the resume carries edited_localized_slides for slide 1
    And the workflow state shows the corrected heading
    And no image generation occurs

  Scenario: Fix casing on a completed carousel from the publish page
    Given a completed carousel whose slide 1 heading starts lowercase
    When the user edits the heading on the publish page and saves
    Then the slide row is updated and a republish is triggered
    And the new PDF contains the corrected heading with unchanged images

  Scenario: Post-completion edit converges the checkpoint report (no stale)
    Given a completed carousel whose stored report has a blocking violation
    When the user edits the offending slide so it validates clean and saves
    Then the presentation_validation returned reflects the edited copy
    And the checkpoint holds the fresh non-blocking report
    And the pending interrupt on the approved-hold thread is preserved

  Scenario: Over-budget edit is caught before submission
    Given the policy limits slide bodies to 220 characters
    When the user types a 300-character body in the editor
    Then the editor shows the budget violation before submit is enabled

  Scenario: Editing is unavailable during an active revision run
    Given the workflow phase status is in_progress
    When the user opens a slide on the review step
    Then the edit affordance is disabled with a run-in-progress message

  Scenario: A completed edit whose client never republishes still converges
    Given a completed carousel marked needs_republish more than a few minutes ago
    When the workflow watchdog tick runs
    Then the marked carousel is republished from its persisted slides
    And the needs_republish marker is cleared

  Scenario: Editing images is never triggered by a text edit
    Given a completed carousel with rendered slide images
    When the user edits a slide's heading and body and saves
    Then the slide image assets are unchanged
