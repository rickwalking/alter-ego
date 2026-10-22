Feature: Conversation ownership
  As a signed-in user
  I want my conversations to be private
  So that nobody else can read my history or write into it

  A conversation owned by a signed-in user is visible only to its owner and to admins.
  Everyone else gets the same 404 an unknown id gets, so the id's existence is never revealed.

  Background:
    Given the backend is running
    And "owner" is a signed-in editor with a conversation
    And "other" is a different signed-in editor
    And "admin" is a signed-in admin

  Scenario: Anonymous caller cannot stream into a signed-in user's conversation
    Given I have no auth cookies
    When I POST to "/api/conversations/{owner-conv}/chat/stream"
    Then the response status is 404
    And no message is persisted in the conversation

  Scenario: Another user cannot stream into someone else's conversation
    Given I am signed in as "other"
    When I POST to "/api/conversations/{owner-conv}/chat/stream"
    Then the response status is 404
    And no message is persisted in the conversation

  Scenario: Owner and admin can stream into the owner's conversation
    Given I am signed in as "owner" or "admin"
    When I POST to "/api/conversations/{owner-conv}/chat/stream"
    Then the response status is 200
    And I receive SSE token events

  Scenario: Anonymous caller cannot use the non-streaming chat on a signed-in user's conversation
    Given I have no auth cookies
    When I POST to "/api/conversations/{owner-conv}/chat"
    Then the response status is 404

  Scenario: Another user cannot read or delete someone else's conversation
    Given I am signed in as "other"
    When I GET "/api/conversations/{owner-conv}", GET its messages, generate its title or DELETE it
    Then every response status is 404 with "Conversation not found"
    And the conversation still exists for "owner"

  Scenario: Another user's conversation list does not include the owner's conversation
    Given I am signed in as "other"
    When I GET "/api/conversations"
    Then the owner's conversation is not in the items

  Scenario: Unknown conversation answers the same 404 as a foreign one
    Given I have no auth cookies
    When I POST to "/api/conversations/00000000-0000-0000-0000-000000000000/chat/stream"
    Then the response status is 404 with "Conversation not found"

  Scenario: Anonymous visitor keeps chatting in an anonymous conversation
    Given I have no auth cookies
    And I created an anonymous conversation
    When I POST to "/api/conversations/{anon-conv}/chat/stream"
    Then the response status is 200
