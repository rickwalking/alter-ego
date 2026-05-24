Feature: WebSocket Authentication
  As a chat user
  I want to authenticate via subprotocol or cookie
  So that the server accepts my WebSocket connection

  Background:
    Given a conversation exists

  Scenario: Authenticate via subprotocol with valid access token
    Given a valid access token "token_abc"
    When I open a WebSocket to "/ws/chat/{conversation_id}" with subprotocol "token_abc"
    Then the connection should be accepted
    And the response should not include Sec-WebSocket-Protocol header

  Scenario: Authenticate via subprotocol with valid anonymous token
    Given a valid anonymous token "anon_xyz" for this conversation
    When I open a WebSocket to "/ws/chat/{conversation_id}" with subprotocol "anon_xyz"
    Then the connection should be accepted

  Scenario: Authenticate via cookie when subprotocol is absent
    Given a valid access_token cookie is set for this conversation
    When I open a WebSocket to "/ws/chat/{conversation_id}" without subprotocol
    Then the connection should be accepted
    And the response should not include Sec-WebSocket-Protocol header

  Scenario: Authenticate via anonymous cookie when subprotocol is absent
    Given a valid anon_token cookie is set for this conversation
    When I open a WebSocket to "/ws/chat/{conversation_id}" without subprotocol
    Then the connection should be accepted

  Scenario: Reject connection with expired access token
    Given an expired access token "expired_token"
    When I open a WebSocket to "/ws/chat/{conversation_id}" with subprotocol "expired_token"
    Then the connection should be closed with code 1008

  Scenario: Reject connection with anonymous token for wrong conversation
    Given a valid anonymous token "anon_wrong" for a different conversation
    When I open a WebSocket to "/ws/chat/{conversation_id}" with subprotocol "anon_wrong"
    Then the connection should be closed with code 1008

  Scenario: Reject connection without any token
    Given no authentication is provided
    When I open a WebSocket to "/ws/chat/{conversation_id}" without subprotocol
    Then the connection should be closed with code 1008

  Scenario: Send and receive message via authenticated WebSocket
    Given I am connected to "/ws/chat/{conversation_id}" with valid authentication
    When I send a JSON message with content "Hello"
    Then I should receive a streaming response starting with token events
    And the stream should end with a complete event

  Scenario: Query param token is not supported
    Given a valid access token "token_query"
    When I open a WebSocket to "/ws/chat/{conversation_id}?token=token_query" without subprotocol
    Then the connection should be closed with code 1008
