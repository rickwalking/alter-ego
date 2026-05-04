Feature: Anonymous Visitor Chat

  Scenario: Visitor starts an anonymous conversation
    When I send a POST request to "/api/conversations" without authentication
    Then the response status should be 201
    And the response should contain a conversation_id
    And the response should set an "anon_token" HttpOnly cookie

  Scenario: Visitor connects to WebSocket with anonymous token
    Given I have an anonymous conversation with token "anon_token_123"
    When I open a WebSocket to "/ws/chat/{conversation_id}?token=anon_token_123"
    Then the connection should be accepted

  Scenario: Visitor cannot access conversation list
    When I send a GET request to "/api/conversations" without authentication
    Then the response status should be 401

  Scenario: Anonymous token expires
    Given an anonymous token that expired 1 hour ago
    When I open a WebSocket with that token
    Then the connection should be closed with code 1008

  Scenario: Visitor can chat via fallback API
    Given I have an anonymous conversation
    When I send a POST request to "/api/conversations/{id}/chat" with:
      | content | Hello |
    Then the response status should be 200
    And the response should contain assistant content
