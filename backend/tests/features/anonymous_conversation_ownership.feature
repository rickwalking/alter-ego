Feature: Anonymous conversation ownership
  As an anonymous visitor on the public chat
  I want my conversation to be mine for as long as my page is open
  So that nobody who learns its id can write into it or read its history through the agent

  The anon_token cookie set when a visitor creates a conversation names that conversation.
  Writing into an anonymous conversation requires a valid token for it; anything else gets the
  same 404 an unknown id gets.

  Scenario: The visitor keeps chatting in the conversation they created
    Given visitor A created an anonymous conversation and holds its anon_token cookie
    When visitor A streams and sends messages into it
    Then the responses are 200

  Scenario: Another visitor cannot write into someone else's anonymous conversation
    Given visitor A created an anonymous conversation
    And visitor B created their own and holds its anon_token
    When visitor B streams or sends a message into visitor A's conversation
    Then the response status is 404 with "Conversation not found"
    And nothing is saved into visitor A's conversation

  Scenario: A signed-in user cannot write into an anonymous conversation
    Given visitor A created an anonymous conversation
    When a signed-in user without its anon_token, or with another conversation's, streams into it
    Then the response status is 404

  Scenario: A missing, expired or tampered token is rejected
    Given visitor A created an anonymous conversation
    When a caller sends no anon_token, an expired one, one signed with another key, or one in the URL
    Then the response status is 404
    And nothing is saved into visitor A's conversation

  Scenario: A visitor with two open conversations can write into both
    Given a visitor created a conversation and then a second one (another tab or New chat)
    Then each conversation's token cookie is scoped to its own URLs
    And the visitor can still write into the first one
