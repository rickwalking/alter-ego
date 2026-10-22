Feature: Chat stream state
  As a visitor or a signed-in user chatting with the Alter-Ego
  I want every reply to render exactly as it was streamed, in one bubble
  So that I can read it, and so a slow network or a double press never loses or duplicates my message

  Scenario: Tokens that arrive in one batch render once, in order
    Given a reply is streaming
    When several tokens arrive before React renders
    Then the reply shows each token exactly once, in order

  Scenario: The first token and a reply that ends in the same batch are kept in one bubble
    Given a reply is streaming
    When its first tokens and the end of the stream arrive in the same batch
    Then the reply keeps its first token
    And the reply stays in a single bubble

  Scenario: A double send while the conversation is being created sends one message
    Given no conversation exists yet
    When I press Send twice before the conversation is created
    Then one conversation is created
    And one message is streamed

  Scenario: The message shows as pending while the conversation is created
    Given no conversation exists yet
    When I send a message
    Then my message bubble and the typing indicator show before the conversation exists
    And the composer is disabled

  Scenario: A failed send keeps the bubble and gives the text back
    When creating the conversation or streaming the reply fails
    Then my message bubble stays
    And the error is shown
    And the composer holds my text again

  Scenario: Resending after a failure replaces the failed bubble
    Given my previous message failed and got no reply
    When I send again
    Then the failed bubble is replaced by the new one

  Scenario: New replies scroll into view
    Given I am reading the bottom of the conversation
    When a new message or streamed text arrives
    Then the list scrolls to the bottom

  Scenario: A reader who scrolled up is not pulled down
    Given I scrolled up to read an earlier message
    When streamed text arrives
    Then the list keeps my scroll position
