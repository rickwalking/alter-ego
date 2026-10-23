Feature: Chat polish
  As a first-time visitor or a returning user
  I want the chat to introduce itself, grow with my message and let me stop a reply
  So that starting and steering a conversation takes no guesswork

  Scenario: An empty chat introduces the Alter-Ego and suggests questions
    Given a chat with no messages
    Then I see who the Alter-Ego is and four suggested questions in my language
    When I pick a suggestion
    Then it is sent as my message

  Scenario: The message box grows with multi-line text
    When I type several lines
    Then the message box grows up to 160px and then scrolls

  Scenario: A streaming reply can be stopped
    Given a reply is streaming
    Then Send turns into "Stop the reply"
    When I press it
    Then the reply stops and the text that arrived stays

  Scenario: The typing label is plain language
    Given a reply is streaming
    Then the typing indicator says "Alter-Ego is typing…"

  Scenario: The conversation and the message box share one readable column
    Given a wide screen
    Then the messages, the "not saved" note and the message box line up in one centred column

  Scenario: Stopping re-reads the history so the saved reply shows
    Given a signed-in user stops a reply
    Then the conversation and the list are re-read
    And on the public chat, which keeps no history, nothing is re-read

  Scenario: A stopped reply is replaced by the reply saved for the same question
    When the reply saved for this question starts with the stopped text
    Then only the saved reply shows
    And a stopped text that merely starts an older answer stays on screen

  Scenario: After a stop the next message is sent
    Given I stopped a reply
    When I send another message
    Then it is sent and answered
    And the stopped text does not come back next to the saved reply

  Scenario: A suggestion picked while a reply is on its way is not sent
    Given a reply is still being written
    When I pick a suggested question
    Then nothing more is sent

  Scenario: A failed reply is re-read from the history
    Given a signed-in user's reply failed
    Then the conversation is re-read, so the saved question and apology replace the on-screen copies
