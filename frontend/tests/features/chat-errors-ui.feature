Feature: Chat errors and message limits in the UI
  As a visitor or signed-in user chatting with the Alter-Ego
  I want failures explained in my language with a way forward
  So that I never see "HTTP 422", "Failed to fetch" or a stack message

  Scenario: Each failure shows a plain, localized message
    When a send fails because I am offline, hit a limit, or the server failed
    Then the chat shows a short message in my language for that case
    And no status code or exception text is shown

  Scenario: An over-long message explains the limit instead of "HTTP 422"
    When the server rejects my message as too long
    Then the chat says to keep it under 2000 characters
    And no Retry is offered

  Scenario: A signed-in user whose session expired is told to sign in again
    Given I am on the dashboard chat
    When my send is rejected because the conversation is not found
    Then the session is re-checked
    And an expired session goes to the login page (session expired) and returns to the chat
    And a valid session sees "This conversation is no longer available"

  Scenario: Retry sends the failed message again
    Given my last message failed
    When I press Try again
    Then the same message is sent again
    And the composer no longer holds it

  Scenario: The composer stops at 2000 characters and shows a counter near the limit
    When I type or paste a long message
    Then the composer accepts at most 2000 characters
    And a "n of 2000 characters" counter shows from 1600 characters

  Scenario: An expired or missing conversation offers a new chat
    Given my visitor conversation passed its 60-minute limit, or the conversation was deleted
    When my send is rejected because the conversation is not found
    Then the chat says "This conversation is no longer available. Start a new chat."
    And a "Start a new chat" button opens a fresh conversation
