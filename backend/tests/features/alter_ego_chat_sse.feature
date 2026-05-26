Feature: Alter-Ego Public Chat Streaming
  As an anonymous or authenticated user
  I want to chat with Pedro's Alter-Ego
  So that I can learn about his career, skills, and experience

  Background:
    Given the backend is running
    And a conversation exists with title "Test Chat"

  # Happy path — authenticated user
  Scenario: Authenticated user sends a message and receives streamed tokens
    Given I am authenticated as user "alice"
    When I POST to "/api/conversations/{conv-id}/chat/stream" with body:
      """
      {"content": "What is your favorite programming language?"}
      """
    Then the response status is 200
    And the Content-Type is "text/event-stream"
    And the Cache-Control is "no-cache"
    And I receive SSE events in order:
      | type   | field    | condition       |
      | token  | content  | non-empty string |
      | token  | content  | non-empty string |
      | sources| sources  | array of objects |
      | complete| -       | event received   |
    And the user message is persisted in the database
    And the assistant message is persisted with non-empty content
    And the assistant message sources are populated

  # Happy path — anonymous user (no auth)
  Scenario: Anonymous user streams chat without any auth
    Given I have no auth cookies
    When I POST to "/api/conversations/{conv-id}/chat/stream" with body:
      """
      {"content": "Hello"}
      """
    Then the response status is 200
    And I receive at least one token event
    And no auth cookie is set in the response

  # Edge case — empty message
  Scenario: User sends empty message
    Given I am authenticated
    When I POST to "/api/conversations/{conv-id}/chat/stream" with body:
      """
      {"content": ""}
      """
    Then the response status is 200
    And I receive an error event with content "Message content cannot be empty"

  # Edge case — conversation not found
  Scenario: Chat for non-existent conversation
    Given I am authenticated
    When I POST to "/api/conversations/00000000-0000-0000-0000-000000000000/chat/stream"
    Then the response status is 200
    And I receive an error event with content "Conversation 00000000-0000-0000-0000-000000000000 not found"

  # Edge case — rate limit (per-conversation message cap)
  Scenario: Anonymous user exceeds conversation message limit
    Given I am anonymous
    And I have sent 19 messages in the current ephemeral conversation
    When I POST to "/api/conversations/{conv-id}/chat/stream" with the 20th message
    Then the response status is 429
    And the response contains "Conversation limit reached"

  # Edge case — rate limit (slowapi per-minute)
  Scenario: User exceeds per-minute rate limit
    Given I am authenticated
    And I have sent 10 messages in the last minute
    When I POST to "/api/conversations/{conv-id}/chat/stream"
    Then the response status is 429
    And no SSE stream is started

  # Edge case — conversation exists but is ephemeral
  Scenario: Anonymous user refreshes page and old conversation is gone
    Given I am anonymous
    And I had a conversation "old-conv" from a previous page load
    When I navigate to "/chat" again
    Then a new conversation is created
    And I cannot access conversation "old-conv" messages
    And no "anon_token" cookie exists

  # Failure — agent error mid-stream
  Scenario: Agent throws exception during token generation
    Given I am authenticated
    And the agent is configured to fail after emitting 2 tokens
    When I POST to "/api/conversations/{conv-id}/chat/stream"
    Then the response status is 200
    And I receive exactly 2 token events
    And I receive an error event with non-empty content
    And the stream ends gracefully
    And no partial assistant message is persisted

  # Failure — database error during user message persist
  Scenario: Database unavailable when persisting user message
    Given I am authenticated
    And the database connection is severed
    When I POST to "/api/conversations/{conv-id}/chat/stream"
    Then the response status is 500 or 503
    And no SSE events are emitted
    And no assistant message is created

  # Persistence — user message committed before streaming
  Scenario: User message is available immediately after stream starts
    Given I am authenticated
    When I POST to "/api/conversations/{conv-id}/chat/stream"
    Then the first SSE event is received
    And when I query "/api/conversations/{conv-id}/messages"
    Then the user message appears in the history

  # Streaming behavior — keep-alive
  Scenario: Slow agent response does not disconnect
    Given I am authenticated
    And the agent takes 25 seconds to respond
    When I POST to "/api/conversations/{conv-id}/chat/stream"
    Then the connection remains open
    And keep-alive pings are received every 15 seconds
    And the first token arrives within 30 seconds

  # Last-Event-ID — resumability
  Scenario: Client resumes stream after connection drop
    Given I am authenticated
    When I POST to "/api/conversations/{conv-id}/chat/stream"
    And I receive 3 token events with ids 1, 2, 3
    And the connection drops
    When I retry the POST with header "Last-Event-ID: 3"
    Then I receive token events with ids greater than 3
    And the complete event is received
