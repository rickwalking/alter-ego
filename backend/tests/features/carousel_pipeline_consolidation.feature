# Carousel Pipeline Consolidation — Backend & API
# Traceability: docs/plans/carousel-pipeline-consolidation.md §15–§16
# Tags: @cp-consolidation

@cp-consolidation @cp-workflow
Feature: Unified editorial workflow API
  As the content platform
  I want a single workflow API surface
  So that carousel generation is not split across legacy and editorial pipelines

  Background:
    Given I am authenticated as an editor
    And a carousel project exists with attached source materials

  @cp-happy-path
  Scenario: Start workflow and pause at first human gate
    When I send a POST request to "/api/carousels/{project_id}/workflow/start"
    Then the response status should be 200
    And the workflow state current_phase should be "research"
    And the workflow state phase_status should be "awaiting_human"
    And the workflow state research_findings should not be empty

  @cp-happy-path
  Scenario: Approve research advances to outline generation inside graph
    Given the workflow is awaiting human review at phase "research"
    When I send a POST request to "/api/carousels/{project_id}/workflow/resume" with body:
      | action  | approve |
    Then the response status should be 202
    And the response should return within 2 seconds
    And the workflow eventually reaches phase "outline" with phase_status "awaiting_human"
    And the workflow state outline should not be empty

  @cp-edge @cp-revise
  Scenario: Revise research loops in-graph without stuck END checkpoint
    Given the workflow is awaiting human review at phase "research"
    When I send a POST request to "/api/carousels/{project_id}/workflow/resume" with body:
      | action   | revise                                      |
      | feedback | Include more recent sources from primary URLs |
    Then the response status should be 202
    And the workflow state phase_status should eventually be "in_progress" or "awaiting_human"
    And the workflow state current_phase should remain "research"
    And the graph checkpoint next nodes should not be empty while awaiting human review

  @cp-edge @cp-revise
  Scenario: Revise after prior revise still accepts approve
    Given the workflow is awaiting human review at phase "outline"
    And I have revised the outline once with feedback "Merge slides 3 and 4"
    When I send a POST request to "/api/carousels/{project_id}/workflow/resume" with body:
      | action  | approve |
    Then the response status should be 202
    And the workflow state current_phase should advance beyond "outline"

  @cp-edge @cp-feedback
  Scenario: Stored feedback is passed to regeneration on revise
    Given the workflow is awaiting human review at phase "content"
    When I send a POST request to "/api/carousels/{project_id}/workflow/resume" with body:
      | action   | revise                         |
      | feedback | Slide 2 tone is too formal     |
    Then the workflow state phase_feedback for "content" should include "Slide 2 tone is too formal"
    And the regenerated slide drafts should reflect the revision request

  @cp-edge @cp-revision-cap
  Scenario: Revision cap triggers escalation
    Given the workflow revision_count for phase "content" is 5
    When I send a POST request to "/api/carousels/{project_id}/workflow/resume" with body:
      | action   | revise              |
      | feedback | Try again           |
    Then the response status should be 409 or 422
    And an admin escalation notification should be created

  @cp-edge @cp-lock
  Scenario: Optimistic lock conflict on concurrent resume
    Given the workflow is awaiting human review at phase "research"
    And the workflow expected_version is 3
    When I send a POST request to "/api/carousels/{project_id}/workflow/resume" with body:
      | action           | approve |
      | expected_version | 2       |
    Then the response status should be 409
    And the workflow state should remain unchanged

@cp-consolidation @cp-artifacts
Feature: Phase artifacts at human gates
  As a reviewer
  I want non-empty artifacts at every gate
  So that I can make informed approve or revise decisions

  @cp-happy-path
  Scenario: Content gate includes slide drafts and persona scores
    Given the workflow is awaiting human review at phase "content"
    When I send a GET request to "/api/carousels/{project_id}/workflow/state"
    Then the workflow state slide_drafts should not be empty
    And the interrupt payload should include persona voice scores

  @cp-edge @cp-persona
  Scenario: Content approve blocked when persona score below threshold
    Given the workflow is awaiting human review at phase "content"
    And the persona voice match score is 65
    When I send a POST request to "/api/carousels/{project_id}/workflow/resume" with body:
      | action  | approve |
    Then the response status should be 422
    And the response detail should mention persona threshold

  @cp-happy-path
  Scenario: Design gate includes design_applied and preview metadata
    Given the workflow is awaiting human review at phase "design"
    When I send a GET request to "/api/carousels/{project_id}/workflow/state"
    Then the workflow state design_applied should be true
    And design tokens should be present on the project

  @cp-happy-path
  Scenario: Images gate includes image asset references
    Given the workflow is awaiting human review at phase "images"
    When I send a GET request to "/api/carousels/{project_id}/workflow/state"
    Then the workflow state image_assets should not be empty

  @cp-happy-path
  Scenario: Final review gate includes blog caption and rubric scores
    Given the workflow is awaiting human review at phase "final_review"
    When I send a GET request to "/api/carousels/{project_id}/workflow/state"
    Then the workflow state should include blog markdown for at least one locale
    And the workflow state should include caption draft
    And the workflow state rubric_scores should not be empty

  @cp-edge @cp-final-review
  Scenario: Final review revise routes to selected earlier phase
    Given the workflow is awaiting human review at phase "final_review"
    When I send a POST request to "/api/carousels/{project_id}/workflow/resume" with body:
      | action              | revise        |
      | feedback            | Rewrite intro |
      | structured_feedback   | {"target_phase":"content"} |
    Then the workflow state current_phase should become "content"
    And the workflow state phase_status should eventually be "awaiting_human"

@cp-consolidation @cp-stream
Feature: Unified workflow progress streaming
  As the create workspace UI
  I want granular progress from the editorial stream only
  So that legacy stream polling is not required

  @cp-happy-path
  Scenario: Stream emits progress during in_progress phase
    Given the workflow phase_status is "in_progress" at phase "images"
    When I open an SSE connection to "/api/carousels/{project_id}/workflow/stream"
    Then I should receive a "progress" event with phase "images"
    And the event should include step message and percent

  @cp-edge @cp-stream-idle
  Scenario: Stream does not emit legacy idle pending loops
    Given the workflow phase_status is "awaiting_human"
    When I open an SSE connection to "/api/carousels/{project_id}/workflow/stream"
    Then I should not receive repeating idle "pending" progress events
    And the frontend should not call "/api/carousels/{project_id}/stream"

  @cp-happy-path
  Scenario: Phase progress persists on project row for reload
    Given the workflow emitted progress for phase "design"
    When I send a GET request to "/api/carousels/{project_id}/workflow/state"
    Then the project phase_progress should mirror the latest progress snapshot

  @cp-happy-path @cp-sse-primary
  Scenario: SSE delivers phase_change without polling during approve
    Given the workflow is awaiting human review at phase "research"
    And a client is subscribed to "/api/carousels/{project_id}/workflow/stream"
    When I send a POST request to "/api/carousels/{project_id}/workflow/resume" with body:
      | action  | approve |
    Then the client should receive a "phase_change" SSE event
    And no workflow state poll should be required to update the client phase

  @cp-happy-path @cp-sse-primary
  Scenario: Stream emits initial snapshot on connect
    Given the project phase_progress snapshot exists for phase "images"
    When I open an SSE connection to "/api/carousels/{project_id}/workflow/stream"
    Then I should receive a "phase_change" event with the current phase
    And I should receive a "progress" event with the persisted phase_progress snapshot
    And the progress snapshot should match GET "/api/carousels/{project_id}/workflow/state" phase_progress

  @cp-happy-path @cp-sse-primary
  Scenario: Live progress events arrive during long resume without state polling
    Given the workflow is awaiting human review at phase "images"
    And a client is subscribed to "/api/carousels/{project_id}/workflow/stream"
    When I send a POST request to "/api/carousels/{project_id}/workflow/resume" with body:
      | action  | approve |
    And image generation publishes progress for slide 3 of 10
    Then the client should receive a "progress" SSE event before the resume response completes
    And the progress event phase_progress current should be 3
    And the progress event phase_progress total should be 10
    And no workflow state poll should be required to update progress

  @cp-happy-path @cp-sse-primary
  Scenario: Progress events include nested phase_progress payload
    Given the workflow phase_status is "in_progress" at phase "images"
    When a progress event is published to the workflow SSE hub
    Then the SSE payload should include a nested phase_progress object
    And phase_progress should include current total label and slides fields

  @cp-edge @cp-sse-primary
  Scenario: Multiple progress events increase monotonically during parallel image generation
    Given a client is subscribed to "/api/carousels/{project_id}/workflow/stream"
    And image generation runs in parallel for 5 slides
    When each slide completion publishes progress
    Then progress event phase_progress current values should be non-decreasing
    And the final progress event phase_progress current should equal total

  @cp-edge @cp-sse-primary
  Scenario: Multiple SSE subscribers receive the same progress event
    Given two clients are subscribed to "/api/carousels/{project_id}/workflow/stream"
    When a single progress event is published for the project
    Then both clients should receive the same progress payload

  @cp-edge @cp-stream-idle
  Scenario: Stream sends keepalive without repeating progress at human gate
    Given the workflow phase_status is "awaiting_human" at phase "design"
    And a client is subscribed to "/api/carousels/{project_id}/workflow/stream"
    When I wait 35 seconds on the open SSE connection
    Then I should receive at most one "phase_change" event at connect
    And I should not receive repeating "progress" events
    And the connection should remain open with keepalive comments

  @cp-edge @cp-sse-primary
  Scenario: SSE stream stays open during resume longer than keepalive interval
    Given a client is subscribed to "/api/carousels/{project_id}/workflow/stream"
    And the workflow is awaiting human review at phase "images"
    When I send a POST request to "/api/carousels/{project_id}/workflow/resume" with body:
      | action  | approve |
    And the resume operation runs longer than 30 seconds
    Then the SSE connection should remain open
    And keepalive comments should be sent while idle
    And live "progress" events should still arrive when image generation publishes updates

@cp-consolidation @cp-sse-rate-limit
Feature: Workflow state read access without public rate limiting
  As an authenticated editor
  I want workflow state reads to succeed during SSE fallback
  So that degraded transport does not block the create workspace

  Background:
    Given I am authenticated as an editor
    And a carousel project exists with attached source materials

  @cp-happy-path @cp-sse-rate-limit
  Scenario: Rapid workflow state reads do not return 429
    Given the workflow is awaiting human review at phase "research"
    When I send 20 GET requests to "/api/carousels/{project_id}/workflow/state" within 10 seconds
    Then all responses should have status 200
    And no response should have status 429

  @cp-edge @cp-sse-rate-limit
  Scenario: Fallback polling burst stays under rate limit after SSE disconnect
    Given a client is subscribed to "/api/carousels/{project_id}/workflow/stream"
    And the workflow phase_status is "in_progress" at phase "images"
    When the SSE connection errors or closes unexpectedly
    And the client polls "/api/carousels/{project_id}/workflow/state" with backoff for 30 seconds
    Then no poll response should have status 429

@cp-consolidation @cp-sse-auth
Feature: Workflow SSE stream access control
  As the platform
  I want workflow SSE restricted to authorized editors
  So that draft progress is never exposed publicly

  Background:
    And a carousel project exists with attached source materials

  @cp-edge @cp-sse-auth
  Scenario: Unauthenticated workflow stream returns 401
    When I open an SSE connection to "/api/carousels/{project_id}/workflow/stream" without authentication
    Then the response status should be 401

  @cp-edge @cp-sse-auth
  Scenario: Editor without project access cannot subscribe to workflow stream
    Given I am authenticated as an editor without access to the project
    When I open an SSE connection to "/api/carousels/{project_id}/workflow/stream"
    Then the response status should be 403 or 404

  @cp-edge @cp-sse-auth
  Scenario: Unauthenticated workflow state returns 401
    When I send a GET request to "/api/carousels/{project_id}/workflow/state" without authentication
    Then the response status should be 401

@cp-consolidation @cp-sse-fallback
Feature: SSE fallback polling for workflow state
  As the create workspace client
  I want polling only when SSE fails
  So that status updates stay real-time without unnecessary load

  @cp-edge @cp-sse-fallback
  Scenario: Polling fallback activates only when SSE disconnects
    Given the create workspace is subscribed to "/api/carousels/{project_id}/workflow/stream"
    When the SSE connection errors or closes unexpectedly
    Then the client should enter polling-fallback mode
    And the client should poll "/api/carousels/{project_id}/workflow/state" with backoff

  @cp-edge @cp-sse-fallback
  Scenario: Polling fallback stops when SSE reconnects
    Given the client is in polling-fallback mode
    When the SSE connection is re-established successfully
    Then the client should stop interval polling
    And subsequent updates should arrive via SSE events only

  @cp-edge @cp-sse-fallback
  Scenario: Polling fallback does not run while SSE is healthy during loading
    Given the create workspace is subscribed to "/api/carousels/{project_id}/workflow/stream"
    And the editorial workflow is awaiting human review at phase "images"
    When I approve the phase and loading is true
    Then the client should remain in SSE primary transport mode
    And the client should not poll "/api/carousels/{project_id}/workflow/state" on an interval

  @cp-edge @cp-sse-fallback
  Scenario: Polling fallback stops at awaiting_human gate
    Given the client is in polling-fallback mode
    And the workflow phase_status becomes "awaiting_human"
    When fallback polling would next run
    Then interval polling should stop
    And subsequent gate updates should rely on SSE or manual refresh only

@cp-consolidation @cp-visibility
Feature: Blog visibility and preview separation
  As the platform
  I want draft carousels hidden from public routes
  So that unpublished content never appears on the public blog

  @cp-happy-path
  Scenario: Anonymous user reads public blog when is_public is true
    Given a carousel project exists with is_public true
    When I send a GET request to "/api/carousels/{project_id}/blog/pt" without authentication
    Then the response status should be 200

  @cp-edge @cp-visibility-draft
  Scenario: Anonymous user cannot read draft blog on public media route
    Given a carousel project exists with is_public false
    When I send a GET request to "/api/carousels/{project_id}/blog/pt" without authentication
    Then the response status should be 404

  @cp-edge @cp-visibility-admin
  Scenario: Admin cannot read draft blog on public media route
    Given a carousel project exists with is_public false
    And I am authenticated as an admin
    When I send a GET request to "/api/carousels/{project_id}/blog/pt"
    Then the response status should be 404

  @cp-happy-path
  Scenario: Editor previews draft blog via preview route
    Given a carousel project exists with is_public false
    And I am authenticated as an editor with project access
    When I send a GET request to "/api/carousels/{project_id}/preview/blog/pt"
    Then the response status should be 200

  @cp-edge @cp-visibility-draft
  Scenario: Anonymous user cannot access preview route
    Given a carousel project exists with is_public false
    When I send a GET request to "/api/carousels/{project_id}/preview/blog/pt" without authentication
    Then the response status should be 401

  @cp-happy-path
  Scenario: Final review approve does not set is_public
    Given the workflow is awaiting human review at phase "final_review"
    When I send a POST request to "/api/carousels/{project_id}/workflow/resume" with body:
      | action  | approve |
    Then the project is_public should be false
    And the workflow_status should be "approved_for_publish"

  @cp-happy-path
  Scenario: Explicit publish sets is_public
    Given a carousel project with workflow_status "approved_for_publish"
    When I send a POST request to "/api/carousels/{project_id}/publish"
    Then the response status should be 200
    And the project is_public should be true

@cp-consolidation @cp-legacy-removal
Feature: Legacy carousel generation endpoints removed
  As the platform
  I want legacy pipeline endpoints gone
  So that only the editorial workflow drives generation

  @cp-happy-path
  Scenario: Legacy generate endpoint returns 404 or 410
    When I send a POST request to "/api/carousels/{project_id}/generate"
    Then the response status should be 404 or 410

  @cp-happy-path
  Scenario: Legacy stream endpoint returns 404 or 410
    When I send a GET request to "/api/carousels/{project_id}/stream"
    Then the response status should be 404 or 410

  @cp-happy-path
  Scenario: Caption endpoint does not run full legacy pipeline
    Given a carousel project with workflow caption already in state
    When I send a POST request to "/api/carousels/{project_id}/caption"
    Then the response should return within 2 seconds
    And no legacy pipeline checkpoint should be created

@cp-consolidation @cp-skills
Feature: Progressive disclosure for carousel skills
  As the RAG agent runtime
  I want phase-scoped skills instead of a monolithic parent skill
  So that context stays minimal per subagent

  @cp-happy-path
  Scenario: Shared standards files exist after migration
    Then the file "skills/carousel-pipeline/_shared/content-contracts.md" should exist
    And the file "skills/carousel-pipeline/_shared/anti-patterns.md" should exist
    And the file "skills/carousel-pipeline/phases/content/SKILL.md" should exist

  @cp-happy-path
  Scenario: Monolithic workflow content is preserved in shared standards
    Then "skills/carousel-pipeline/_shared/content-contracts.md" should mention slide types intro content closing cta
    And "skills/carousel-pipeline/_shared/design-system.md" should mention 1080x1350 typography
    And "skills/carousel-pipeline/_shared/image-generation.md" should mention scene description only

  @cp-edge @cp-skills
  Scenario: RAG parent agent does not load full carousel pipeline skill
    When the RAG agent is initialized
    Then its skills configuration should not include the monolithic "skills/carousel-pipeline" bundle on the parent

@cp-consolidation @cp-rag
Feature: RAG carousel tool uses editorial workflow
  As a chat user
  I want carousel creation to start the editorial workflow
  So that chat and create workspace share one pipeline

  @cp-happy-path
  Scenario: Generate carousel tool starts workflow not legacy pipeline
    Given I am authenticated as an editor
    And a carousel project exists
    When the RAG agent invokes the generate_carousel tool for the project
    Then the editorial workflow state should exist for the project
    And no legacy execute_pipeline run should have started

@cp-consolidation @cp-standards
Feature: Content standards enforcement in generated artifacts
  As the platform
  I want carousel standards enforced in code
  So that skill contracts are not documentation-only

  @cp-happy-path
  Scenario: Generated slide content strips em dashes
    Given the workflow completed content generation
    Then no slide draft text should contain em dash characters

  @cp-edge @cp-standards
  Scenario: Invalid content JSON fails loudly without stub slide
    Given the content subagent returns unparseable JSON
    Then the workflow phase_status should be "failed" or retry with error event
    And the project should not contain a single stub intro slide marked completed

  @cp-happy-path
  Scenario: Closing slide uses structured checklist not prose wall
    Given the workflow completed content generation
    Then the closing slide should include structured checklist items or features array

@cp-consolidation @cp-recovery
Feature: Workflow checkpoint recovery
  As an editor
  I want workflows to survive restarts
  So that long editorial sessions are not lost

  @cp-edge @cp-recovery
  Scenario: Resume workflow after server restart
    Given the workflow is awaiting human review at phase "content"
    When the application restarts
    And I send a GET request to "/api/carousels/{project_id}/workflow/state"
    Then the workflow state current_phase should be "content"
    And the workflow state phase_status should be "awaiting_human"
    And the workflow state slide_drafts should not be empty

@cp-consolidation @cp-resume-gap
Feature: Resume transport resilience and artifact readiness
  As the editorial workflow API
  I want resume to be decoupled from artifact availability checks
  So that clients can recover when HTTP transport fails but generation succeeds

  Background:
    Given I am authenticated as an editor
    And a carousel project exists with attached source materials

  @cp-edge @cp-resume-gap
  Scenario: Workflow state includes outline artifacts when outline gate opens
    Given the workflow is awaiting human review at phase "outline"
    When I send a GET request to "/api/carousels/{project_id}/workflow/state"
    Then the workflow state outline should not be empty
    And the workflow state phase_status should be "awaiting_human"

  @cp-edge @cp-resume-gap
  Scenario: Workflow state includes slide drafts when content gate opens
    Given the workflow is awaiting human review at phase "content"
    When I send a GET request to "/api/carousels/{project_id}/workflow/state"
    Then the workflow state slide_drafts should not be empty
    And the workflow state slide_drafts count should be at least the outline slide count

  @cp-happy-path @cp-resume-gap @cp-sse-primary
  Scenario: Artifact SSE event published when outline generation completes
    Given a client is subscribed to "/api/carousels/{project_id}/workflow/stream"
    And the workflow phase_status is "in_progress" at phase "outline"
    When outline generation completes
    Then the client should receive an "artifact" SSE event with artifact_type "outline"
    And the artifact payload outline should not be empty

  @cp-happy-path @cp-resume-gap @cp-sse-primary
  Scenario: Artifact SSE event published when content drafts complete
    Given a client is subscribed to "/api/carousels/{project_id}/workflow/stream"
    And the workflow phase_status is "in_progress" at phase "content"
    When content generation completes
    Then the client should receive an "artifact" SSE event with artifact_type "slide_drafts"
    And the artifact payload slide_drafts should not be empty

@cp-consolidation @cp-async-resume
Feature: Async editorial workflow resume
  As the editorial workflow API
  I want resume to return immediately and run generation in the background
  So that HTTP clients and proxies never block on LLM work

  Background:
    Given I am authenticated as an editor
    And a carousel project exists with attached source materials

  @cp-happy-path @cp-async-resume
  Scenario: Approve research returns 202 within 2 seconds
    Given the workflow is awaiting human review at phase "research"
    When I send a POST request to "/api/carousels/{project_id}/workflow/resume" with body:
      | action  | approve |
    Then the response status should be 202
    And the response should return within 2 seconds
    And the response body phase_status should be "in_progress"
    And the workflow eventually reaches phase "outline" with phase_status "awaiting_human"

  @cp-happy-path @cp-async-resume @cp-sse-primary
  Scenario: Background resume publishes review_required when outline gate opens
    Given a client is subscribed to "/api/carousels/{project_id}/workflow/stream"
    And the workflow is awaiting human review at phase "research"
    When I send a POST request to "/api/carousels/{project_id}/workflow/resume" with body:
      | action  | approve |
    Then the response status should be 202
    And the client should receive a "review_required" SSE event for phase "outline"
    And the review_required payload outline should not be empty

  @cp-edge @cp-async-resume
  Scenario: Resume while phase_status is in_progress returns 409
    Given the workflow phase_status is "in_progress" at phase "outline"
    When I send a POST request to "/api/carousels/{project_id}/workflow/resume" with body:
      | action  | approve |
    Then the response status should be 409
    And the response detail should indicate resume already in progress

  @cp-edge @cp-async-resume @cp-lock
  Scenario: Duplicate approve with same expected_version is idempotent
    Given the workflow is awaiting human review at phase "research"
    And the workflow expected_version is 4
    When I send two POST requests to "/api/carousels/{project_id}/workflow/resume" with body:
      | action           | approve |
      | expected_version | 4       |
    Then one response should have status 202
    And the other response should have status 202 or 409
    And the workflow should advance to outline exactly once

  @cp-edge @cp-async-resume
  Scenario: Background resume failure publishes recoverable error event
    Given the workflow is awaiting human review at phase "outline"
    And outline generation will fail in the background worker
    When I send a POST request to "/api/carousels/{project_id}/workflow/resume" with body:
      | action  | approve |
    Then the response status should be 202
    And a client subscribed to "/api/carousels/{project_id}/workflow/stream" should receive an "error" SSE event with recoverable true
    And the workflow state phase_status should eventually be "failed"

  @cp-edge @cp-async-resume @cp-recovery
  Scenario: Server restart during background resume resumes from checkpoint
    Given the workflow phase_status is "in_progress" at phase "content"
    When the application restarts before content generation completes
    And I send a GET request to "/api/carousels/{project_id}/workflow/state"
    Then the workflow state should not be stuck in an unrecoverable state
    And the workflow should eventually reach "awaiting_human" or "failed" with an audit entry
