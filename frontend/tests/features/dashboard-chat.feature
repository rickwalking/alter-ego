Feature: Dashboard chat history
  As a signed-in user
  I want my conversations to be findable, titled, and complete after a refresh
  So that the dashboard chat works as a real history

  Scenario: A reply that was still streaming appears after a refresh
    Given I refreshed while a reply was streaming
    When the conversation reloads with my message but no reply yet
    Then the typing indicator shows and the history is re-read every 2 seconds
    And the reply appears as soon as the server saves it, without another refresh

  Scenario: Polling stops when nothing is awaited
    When the last message is a reply, or my message is older than 3 minutes
    Then the history is not re-read

  Scenario: Conversations show their real titles and no invented avatars
    Then each conversation shows its title (or "New conversation" before the first message) and its time
    And no AE/KB/WF avatars or fake unread dots are shown

  Scenario: The sidebar shows a new conversation's title after its first reply
    When a reply finishes
    Then the conversation list and the history are each re-read once

  Scenario: Searching conversations filters the list
    When I type part of a title in "Search conversations", ignoring case and accents
    Then only matching conversations are listed
    And a "no matches" note shows when none match

  Scenario: An empty search shows every conversation
    When the search box is empty or only spaces
    Then every conversation is listed

  Scenario: A signed-in user opening /chat lands on the dashboard chat
    Given I am signed in
    When I open /chat
    Then I am taken to /dashboard/chat with my history
    And a visitor or an expired session still gets the public chat
