Feature: Chat Interface

  As a user
  I want to chat with the AI about my knowledge base
  So that I can get answers based on my documents

  Scenario: Display chat interface
    Given I navigate to the chat page
    Then I see the chat interface
    And I see a message input field
    And I see a send button
    And I see the conversation sidebar

  Scenario: Send a message
    Given I am on the chat page with an active conversation
    When I type a message in the input field
    And I click the send button
    Then my message appears in the message list
    And the input field is cleared
    And the send button is disabled while loading

  Scenario: Send empty message
    Given I am on the chat page
    When the input field is empty
    Then the send button is disabled

  Scenario: Start a new conversation
    Given I am on the chat page
    When I click the "New Chat" button
    Then the message list is cleared
    And the input field is ready for a new message

  Scenario: Submit message with Enter key
    Given I am on the chat page with an active conversation
    When I type a message in the input field
    And I press Enter without Shift
    Then the message is sent
    And the input field is cleared

  Scenario: New line with Shift+Enter
    Given I am on the chat page
    When I type text in the input field
    And I press Shift+Enter
    Then a new line is added
    And the message is not sent

  Scenario: Conversation sidebar shows conversations
    Given conversations exist in the system
    When I am on the chat page
    Then I see the conversations in the sidebar
    And the active conversation is highlighted

  Scenario: Loading state during message send
    Given I am on the chat page with an active conversation
    When I send a message
    Then the send button shows a loading state
    And the input field is disabled
    And when the response arrives, the loading state is removed
