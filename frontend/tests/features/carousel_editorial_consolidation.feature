# Carousel Pipeline Consolidation — Frontend & Create Workspace
# Traceability: docs/plans/carousel-pipeline-consolidation.md §15–§16
# Tags: @cp-consolidation

@cp-consolidation @cp-ui-workflow
Feature: Editorial workflow panel per-phase review
  As an editor
  I want to see generated artifacts and submit feedback at every phase
  So that I control carousel quality before publish

  Background:
    Given I am logged in as an editor
    And I open the create workspace for carousel project "{project_id}"

  @cp-happy-path
  Scenario: Research gate shows findings and feedback composer
    Given the editorial workflow is awaiting human review at phase "research"
    Then I should see research findings with key points
    And I should see a feedback text area
    And I should see an "Approve" button
    And I should see a "Request revision" button

  @cp-happy-path
  Scenario: Final review tab shows carousel blog caption and quality scores
    Given the editorial workflow is awaiting human review at phase "final_review"
    Then I should see a "Carousel" tab with slide preview
    And I should see a "Blog" tab with markdown preview
    And I should see a "Caption" tab
    And I should see a "Quality" tab with rubric scores

  @cp-edge @cp-ui-revise
  Scenario: Request revision requires feedback text
    Given the editorial workflow is awaiting human review at phase "outline"
    When I click "Request revision" without entering feedback
    Then I should see a validation message that feedback is required
    And the workflow should remain awaiting human review

  @cp-happy-path
  Scenario: Outline revise sends structured reorder payload
    Given the editorial workflow is awaiting human review at phase "outline"
    When I reorder slide 3 above slide 1
    And I enter feedback "Prioritize the breach example first"
    And I click "Request revision"
    Then the workflow should return to generating outline
    And the revised outline order should reflect my reorder

  @cp-edge @cp-ui-persona
  Scenario: Content approve disabled when persona score below threshold
    Given the editorial workflow is awaiting human review at phase "content"
    And the persona voice match score shown is 65
    Then the "Approve" button should be disabled
    And I should see persona threshold guidance

@cp-consolidation @cp-ui-progress
Feature: Unified workflow progress in create workspace
  As an editor
  I want progress only while generation is running
  So that the UI does not poll legacy streams at human gates

  @cp-happy-path
  Scenario: Progress strip active during in_progress only
    Given the editorial workflow phase_status is "in_progress" at phase "images"
    Then I should see image generation progress messages
    And the browser should not request "/api/carousels/{project_id}/stream"

  @cp-edge @cp-stream-idle
  Scenario: No progress polling loop at awaiting_human gate
    Given the editorial workflow phase_status is "awaiting_human" at phase "design"
    When I wait 10 seconds
    Then the browser should not repeatedly request "/api/carousels/{project_id}/stream"
    And I should see the design review artifacts without a spinning legacy progress message

  @cp-happy-path @cp-sse-primary
  Scenario: SSE delivers phase_change without polling during approve
    Given the editorial workflow is awaiting human review at phase "research"
    When I click "Approve"
    Then the workflow phase should advance via SSE phase_change event
    And the browser should not start an interval polling loop for workflow state

  @cp-happy-path @cp-sse-primary
  Scenario: Mount hydrates workflow state once then opens SSE
    When I open the create workspace for carousel project "{project_id}"
    Then the browser should send exactly one GET "/api/carousels/{project_id}/workflow/state" on mount
    And the browser should open one SSE connection to "/api/carousels/{project_id}/workflow/stream"

  @cp-happy-path @cp-sse-primary
  Scenario: Live SSE progress updates slide grid during approve without state polling
    Given the editorial workflow is awaiting human review at phase "images"
    And the create workspace has an active workflow SSE subscription
    When I click "Approve Phase"
    And the backend publishes image progress for slide 3 of 10
    Then I should see slide progress update to 3 of 10
    And the browser should not poll "/api/carousels/{project_id}/workflow/state" on an interval while loading

  @cp-happy-path @cp-sse-primary
  Scenario: SSE progress merges nested phase_progress into client state
    Given the create workspace has an active workflow SSE subscription
    When a "progress" SSE event arrives with nested phase_progress current 4 and total 10
    Then the editorial workflow state phase_progress current should be 4
    And the editorial workflow state phase_progress total should be 10

  @cp-edge @cp-sse-primary
  Scenario: No loading-time workflow state poll while SSE is healthy
    Given the create workspace has an active workflow SSE subscription
    And the editorial workflow is awaiting human review at phase "content"
    When I click "Approve Phase"
    And loading is true for up to 60 seconds
    Then the browser should not poll "/api/carousels/{project_id}/workflow/state" on an interval
    And progress or phase updates should arrive via SSE events only

  @cp-edge @cp-sse-fallback
  Scenario: Polling fallback activates only when SSE disconnects
    Given the create workspace has an active workflow SSE subscription
    When the SSE connection fails
    Then the client should poll "/api/carousels/{project_id}/workflow/state" as fallback
    And polling should use increasing backoff intervals

  @cp-edge @cp-sse-fallback
  Scenario: Polling fallback stops when SSE reconnects
    Given the client is polling workflow state because SSE failed
    When the SSE connection is restored
    Then interval polling should stop
    And the transport mode should return to SSE primary

  @cp-edge @cp-sse-fallback
  Scenario: Fallback polling does not receive 429 from workflow state
    Given the create workspace has an active workflow SSE subscription
    When the SSE connection fails and the client enters polling-fallback mode
    And the client polls "/api/carousels/{project_id}/workflow/state" with backoff for 30 seconds
    Then no poll response should have status 429

  @cp-edge @cp-sse-fallback
  Scenario: Fallback polling stops at awaiting_human gate
    Given the client is polling workflow state because SSE failed
    And the workflow phase_status becomes "awaiting_human"
    When the next fallback poll interval elapses
    Then interval polling should stop

  @cp-edge @cp-stream-idle
  Scenario: No workflow state poll loop after loading completes at human gate
    Given the editorial workflow phase_status is "awaiting_human" at phase "design"
    When I wait 10 seconds after the page finishes loading
    Then the browser should not repeatedly request "/api/carousels/{project_id}/workflow/state"
    And the browser should not poll "/api/carousels/{project_id}/workflow/state" on an interval

  @cp-happy-path
  Scenario: Reload restores persisted phase progress snapshot
    Given image generation progress reached 50 percent
    When I reload the create workspace page
    Then I should see the last persisted progress snapshot
    And the workflow SSE connection should resume updates

@cp-consolidation @cp-ui-visibility
Feature: Public blog and workspace preview separation
  As an editor
  I want draft previews only in the create workspace
  So that public blog URLs never show unpublished content

  @cp-edge @cp-visibility-admin
  Scenario: Admin sees 404 on public blog page for draft carousel
    Given I am logged in as an admin
    And a carousel project exists with is_public false
    When I navigate to "/blog/{project_id}"
    Then I should see a not found page

  @cp-happy-path
  Scenario: Editor previews draft blog inside create workspace
    Given a carousel project exists with is_public false
    And the workflow is at phase "final_review"
    When I open the "Blog" tab in final review
    Then I should see the generated blog markdown preview
    And the page URL should not be the public "/blog/{project_id}" route

  @cp-happy-path
  Scenario: Public blog page has no admin publish panel
    Given a carousel project exists with is_public true
    When I navigate to "/blog/{project_id}" as an admin
    Then I should not see the blog admin publish panel
    And I should see read-only blog content

  @cp-happy-path
  Scenario: Publish panel appears after final review approval
    Given the workflow_status is "approved_for_publish"
    When I navigate to the publish panel for the project
    Then I should see Instagram and LinkedIn publish options
    And I should see an explicit "Publish to site" action

  @cp-happy-path
  Scenario: Publish to site makes public blog accessible
    Given the workflow_status is "approved_for_publish"
    When I click "Publish to site"
    Then the project is_public should become true
    When I navigate to "/blog/{project_id}" without authentication
    Then I should see the published blog content

@cp-consolidation @cp-ui-legacy
Feature: Legacy carousel hooks removed from frontend
  As the frontend codebase
  I want no references to legacy generation endpoints
  So that the UI cannot regress to dual pipeline behavior

  @cp-happy-path
  Scenario: Create workspace does not reference legacy stream constants
    Then the frontend should not import CAROUSEL_STREAM or CAROUSEL_GENERATE constants
    And EditorialWorkflowProgress should subscribe only to CAROUSEL_WORKFLOW_STREAM

@cp-consolidation @cp-ui-final-review
Feature: Final review send-back to earlier phase
  As an editor
  I want to send final review back to a specific phase
  So that I can fix content without restarting the whole workflow

  @cp-happy-path
  Scenario: Send final review back to content phase
    Given the editorial workflow is awaiting human review at phase "final_review"
    When I select send back target "content"
    And I enter feedback "Intro slide needs a personal anecdote"
    And I click "Request revision"
    Then the workflow current_phase should become "content"
    And I should eventually see updated slide drafts at the content gate

@cp-consolidation @cp-resume-gap
Feature: Resume recovery without false errors or manual refresh
  As an editor
  I want approvals to show artifacts automatically
  So that I can review without refreshing when resume transport fails

  Background:
    Given I am logged in as an editor
    And I open the create workspace for carousel project "{project_id}"

  @cp-edge @cp-resume-gap
  Scenario: Resume transport failure does not show error banner when workflow recovers
    Given the editorial workflow is awaiting human review at phase "research"
    And the next POST "/api/carousels/{project_id}/workflow/resume" will fail with status 500 or network error
    When I click "Approve Phase"
    And the workflow eventually reaches phase "outline" with phase_status "awaiting_human"
    Then I should not see an error banner about resuming the workflow
    And the approve action should remain in a loading state until recovery completes or fails definitively

  @cp-happy-path @cp-resume-gap
  Scenario: Outline artifacts appear without manual page refresh after research approval
    Given the editorial workflow is awaiting human review at phase "research"
    When I click "Approve Phase"
    And the workflow reaches phase "outline" with phase_status "awaiting_human"
    Then I should see outline slides in the review panel
    And I should not need to reload the page

  @cp-happy-path @cp-resume-gap
  Scenario: Content slide drafts appear without manual page refresh after outline approval
    Given the editorial workflow is awaiting human review at phase "outline"
    When I click "Approve Phase"
    And the workflow reaches phase "content" with phase_status "awaiting_human"
    Then I should see slide drafts in the review panel
    And I should not need to reload the page

  @cp-edge @cp-resume-gap
  Scenario: Loading state persists until expected artifacts exist for the next gate
    Given the editorial workflow is awaiting human review at phase "research"
    When I click "Approve Phase"
    And the workflow phase_status becomes "awaiting_human" at phase "outline"
    But outline artifacts are not yet present in client state
    Then the approve action should remain loading
    When outline artifacts become available via SSE or state hydration
    Then the approve action should stop loading
    And I should see outline slides in the review panel

  @cp-happy-path @cp-resume-gap @cp-sse-primary
  Scenario: Artifact SSE hydrates review panel during resume recovery
    Given the create workspace has an active workflow SSE subscription
    And the editorial workflow is awaiting human review at phase "research"
    When I click "Approve Phase"
    And an "artifact" SSE event arrives with artifact_type "outline"
    Then the outline review panel should update without a full page reload
    And the browser should not require manual refresh to show outline slides

  @cp-edge @cp-resume-gap @cp-sse-fallback
  Scenario: Polling recovery waits for artifacts not only gate status
    Given the create workspace has an active workflow SSE subscription
    And the editorial workflow is awaiting human review at phase "outline"
    When I click "Approve Phase"
    And POST "/api/carousels/{project_id}/workflow/resume" fails with a transport error
    And GET "/api/carousels/{project_id}/workflow/state" returns phase "content" and phase_status "awaiting_human"
    But slide_drafts are still empty
    Then the client should continue recovery polling
    When slide_drafts become non-empty in workflow state
    Then recovery polling should stop
    And I should see slide drafts in the review panel

@cp-consolidation @cp-async-resume
Feature: Async resume client behavior
  As an editor
  I want immediate feedback on approve without waiting for generation
  So that the UI stays responsive during long phases

  @cp-happy-path @cp-async-resume @cp-sse-primary
  Scenario: Approve clears loading via SSE not resume HTTP response
    Given the editorial workflow is awaiting human review at phase "research"
    And the create workspace has an active workflow SSE subscription
    When I click "Approve Phase"
    And POST "/api/carousels/{project_id}/workflow/resume" returns 202 within 2 seconds
    Then the browser should not poll "/api/carousels/{project_id}/workflow/state" on an interval while SSE is healthy
    And the next gate should open when a "review_required" SSE event arrives

  @cp-edge @cp-async-resume
  Scenario: Double-click approve does not enqueue duplicate background jobs
    Given the editorial workflow is awaiting human review at phase "outline"
    When I double-click "Approve Phase" rapidly
    Then at most one POST "/api/carousels/{project_id}/workflow/resume" should succeed with 202
    And I should not see duplicate phase transitions in the workflow state

  @cp-edge @cp-async-resume @cp-sse-fallback
  Scenario: SSE disconnect during background resume uses polling fallback until gate opens
    Given the editorial workflow is awaiting human review at phase "images"
    And POST "/api/carousels/{project_id}/workflow/resume" returns 202
    When the SSE connection fails during image generation
    Then the client should enter polling-fallback mode
    And polling should stop when phase_status becomes "awaiting_human" and image_assets are non-empty
