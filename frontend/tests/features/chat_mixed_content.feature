Feature: Chat Mixed Content Fix
  As a visitor
  I want to chat with the AI assistant
  So that I can ask questions without mixed content errors

  Scenario: Anonymous user starts a conversation over HTTPS
    Given I am on the chat page
    And the page is served over HTTPS
    When I type a message and send it
    Then the conversation should be created over HTTPS
    And no mixed content warnings should appear in the console

  Scenario: WebSocket connection uses wss protocol on HTTPS
    Given I am on the chat page
    And the page is served over HTTPS
    When the WebSocket connects
    Then the WebSocket URL should use wss://

  Scenario: API requests preserve HTTPS protocol
    Given I am on the chat page
    And the page is served over HTTPS
    When I send any API request
    Then the request should remain on HTTPS
    And there should be no http:// redirects
