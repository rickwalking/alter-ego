Feature: Carousel editorial workflow safety net (AE-0106)
  As the Phase 4 modularization effort
  I need a byte-identical baseline of the carousel workflow API + SSE stream
  So that AE-0107 / AE-0110 / AE-0111 can diff the relocated handlers to zero.

  Background:
    Given the editorial_workflow feature flag is enabled
    And DEBUG is pinned so env-sensitive fields are deterministic local vs CI
    And the workflow service is replaced with a deterministic in-memory stub

  # --- GET /workflow/state ----------------------------------------------------

  Scenario: Workflow state response is unchanged for a mid-workflow project
    Given a carousel project owned by the editor, mid-workflow
    When GET /api/carousels/{id}/workflow/state runs
    Then the response status is 200
    And the body matches the committed snapshot (volatile fields normalized)
    And the snapshot includes artifact URL fields (image_assets, blog_markdown, design_applied)

  Scenario: Workflow state returns 404 when no checkpoint exists
    Given a carousel project owned by the editor with no workflow state
    When GET /api/carousels/{id}/workflow/state runs
    Then the response status is 404
    And the body matches the committed snapshot

  Scenario: Workflow state is forbidden for a non-owner non-reviewer
    Given a carousel project owned by another editor
    When GET /api/carousels/{id}/workflow/state runs as a different editor
    Then the response status is 403

  # --- POST /workflow/start ---------------------------------------------------

  Scenario: Workflow start response is unchanged
    Given a carousel project owned by the editor with no workflow state
    When POST /api/carousels/{id}/workflow/start runs with a valid brief
    Then the response status is 200
    And the body matches the committed snapshot (volatile fields normalized)

  Scenario: Workflow start rejects self-assignment as reviewer
    Given a carousel project owned by the editor
    When POST /api/carousels/{id}/workflow/start names the caller as reviewer
    Then the response status is 400

  # --- POST /workflow/resume + interrupt -> resume gates ----------------------

  Scenario: Workflow resume accepts an approve and returns 202
    Given a carousel project paused at a human review gate
    When POST /api/carousels/{id}/workflow/resume approves with the expected version
    Then the response status is 202
    And the body matches the committed snapshot (volatile fields normalized)
    And the project lock_version is bumped

  Scenario: Workflow resume rejects an unsupported action
    Given a carousel project paused at a human review gate
    When POST /api/carousels/{id}/workflow/resume sends an unsupported action
    Then the response status is 422

  Scenario: Workflow resume requires feedback for a revise action
    Given a carousel project paused at a human review gate
    When POST /api/carousels/{id}/workflow/resume revises with empty feedback
    Then the response status is 422

  Scenario: Workflow resume rejects a stale expected version (optimistic lock)
    Given a carousel project at lock_version 1 paused at a review gate
    When POST /api/carousels/{id}/workflow/resume sends a stale expected version
    Then the response status is 409 with a version_conflict detail

  Scenario: Concurrent resume — only the first bump wins (optimistic lock)
    Given a carousel project at lock_version 1 paused at a review gate
    When two resume requests send the same expected version sequentially
    Then the first returns 202 and the second returns 409 (version_conflict)

  # --- GET /workflow/stream (deterministic mock) ------------------------------

  Scenario: Workflow stream emits the same SSE event sequence
    Given a deterministic mock workflow that yields a fixed event sequence
    When GET /api/carousels/{id}/workflow/stream runs
    Then the SSE event types appear in the snapshot order
    And every emitted event uses id: + event: + data: framing
    And keep-alive comment interleaving is ignored

  Scenario: Workflow stream is falsifiable by a reordered or renamed event
    Given a deterministic mock workflow with a reordered event sequence
    When the asserted event-type order is compared
    Then the assertion fails (the snapshot is not a no-op)

  Scenario: Workflow stream ignores Last-Event-ID (current contract)
    Given a deterministic mock workflow
    When GET /api/carousels/{id}/workflow/stream runs with Last-Event-ID set
    Then the emitted event ids still start at 1 (resume not implemented for this stream)
    And a refactor that silently added resume support would break this assertion
