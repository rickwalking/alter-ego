Feature: Conversation Management

  As a user
  I want to manage chat conversations
  So that I can have persistent chat sessions with the AI

  Scenario: Create conversation with title
    Given a valid conversation payload with title
    When I send POST /api/conversations with the payload
    Then the response status is 201
    And the response contains the conversation with the given title
    And the conversation has a unique ID

  Scenario: Create conversation without title
    Given an empty conversation payload
    When I send POST /api/conversations with the payload
    Then the response status is 201
    And the response contains a conversation with null title

  Scenario: List conversations when none exist
    Given no conversations in the database
    When I send GET /api/conversations
    Then the response status is 200
    And the items list is empty
    And the total count is 0

  Scenario: List conversations with existing conversations
    Given at least one conversation exists
    When I send GET /api/conversations
    Then the response status is 200
    And the items list contains at least one conversation
    And the total count is greater than 0

  Scenario: Get conversation by existing ID
    Given a conversation exists with ID "conv-123"
    When I send GET /api/conversations/conv-123
    Then the response status is 200
    And the response contains the conversation with ID "conv-123"

  Scenario: Get conversation by non-existing ID
    Given no conversation exists with ID "nonexistent"
    When I send GET /api/conversations/nonexistent
    Then the response status is 404
    And the response contains an error message

  Scenario: Get messages for existing conversation
    Given a conversation exists with ID "conv-123"
    When I send GET /api/conversations/conv-123/messages
    Then the response status is 200
    And the response contains the conversation ID
    And the items list may be empty

  Scenario: Get messages for non-existing conversation
    Given no conversation exists with ID "nonexistent"
    When I send GET /api/conversations/nonexistent/messages
    Then the response status is 404
    And the response contains an error message

  Scenario: Delete existing conversation
    Given a conversation exists with ID "conv-123"
    When I send DELETE /api/conversations/conv-123
    Then the response status is 204
    And the conversation is no longer retrievable

  Scenario: Delete non-existing conversation
    Given no conversation exists with ID "nonexistent"
    When I send DELETE /api/conversations/nonexistent
    Then the response status is 404
    And the response contains an error message

  Scenario: Full conversation CRUD lifecycle
    Given an empty database
    When I create a conversation with title "Test"
    And I retrieve the conversation by its ID
    Then the response status is 200
    And the title matches "Test"
    When I delete the conversation
    And I try to retrieve it again
    Then the response status is 404
