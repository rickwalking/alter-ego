Feature: Publish Page Carousel Agent Streaming
  As an authenticated user
  I want to chat with the carousel agent on the publish page
  So that I can refine carousel copy and content

  Background:
    Given the backend is running
    And I am authenticated as user "alice"
    And a carousel project exists with id "proj-123"
    And a conversation exists with metadata {"project_id": "proj-123"}

  # Happy path
  Scenario: Authenticated user refines carousel copy
    Given the conversation is linked to project "proj-123"
    When I POST to "/api/conversations/{conv-id}/publish-chat/stream" with body:
      """
      {"content": "Make the caption shorter"}
      """
    Then the response status is 200
    And the Content-Type is "text/event-stream"
    And I receive SSE events in order:
      | type        | field   | condition      |
      | token       | content | non-empty      |
      | token       | content | non-empty      |
      | tool_result | tool    | "refine_carousel_copy" |
      | complete    | -       | event received |
    And the user message is persisted
    And the assistant message is persisted

  # Auth — anonymous user denied
  Scenario: Anonymous user attempts publish chat
    Given I have no auth cookies
    When I POST to "/api/conversations/{conv-id}/publish-chat/stream"
    Then the response status is 401

  # Auth — wrong user
  Scenario: User tries to access another user's publish chat
    Given I am authenticated as user "bob"
    And the conversation belongs to user "alice"
    When I POST to "/api/conversations/{conv-id}/publish-chat/stream"
    Then the response status is 403

  # Edge case — conversation has no project_id metadata
  Scenario: Publish chat for non-carousel conversation
    Given a conversation exists with no "project_id" metadata
    When I POST to "/api/conversations/{conv-id}/publish-chat/stream"
    Then the response status is 400
    And the response contains "Not a carousel conversation"

  # Tool result — carousel copy refinement
  Scenario: Carousel copy refinement triggers cache invalidation
    Given I am authenticated
    And the conversation is linked to project "proj-123"
    When I POST to "/api/conversations/{conv-id}/publish-chat/stream" with:
      """
      {"content": "Refine the Instagram caption"}
      """
    Then I receive a tool_result event with tool "refine_carousel_copy"
    And the carousel project "proj-123" is updated in the database
    And the assistant message contains the refined copy

  # Tool result — image regeneration
  Scenario: Image regeneration tool is called
    Given I am authenticated
    And the conversation is linked to project "proj-123"
    When I POST to "/api/conversations/{conv-id}/publish-chat/stream" with:
      """
      {"content": "Regenerate the hero image"}
      """
    Then I may receive a tool_result event with tool "regenerate_image"
    And the image is updated in the carousel project

  # Persistence — history kept for authenticated user
  Scenario: Authenticated user refreshes and sees chat history
    Given I am authenticated
    And the conversation is linked to project "proj-123"
    And I have sent 3 messages previously
    When I navigate to the publish page again
    Then the previous 3 messages are visible in the chat history
    And the conversation ID is the same

  # Rate limit
  Scenario: Authenticated user exceeds per-minute rate limit on publish chat
    Given I am authenticated
    And I have sent 10 messages in the last minute
    When I POST to "/api/conversations/{conv-id}/publish-chat/stream"
    Then the response status is 429
    And no SSE stream is started

  # Last-Event-ID — resumability
  Scenario: Client resumes publish stream after connection drop
    Given I am authenticated
    And the conversation is linked to project "proj-123"
    When I POST to "/api/conversations/{conv-id}/publish-chat/stream"
    And I receive 2 token events with ids 1, 2
    And the connection drops
    When I retry the POST with header "Last-Event-ID: 2"
    Then I receive token events with ids greater than 2
    And the complete event is received
