Feature: Searching conversations
  As a signed-in user with a long chat history
  I want to search all my conversations by title
  So that an older conversation is found even when it is not on the first page

  Scenario: Searching conversations finds older ones too
    Given I have more conversations than one page shows
    When I search for part of an older conversation's title
    Then the server returns my matching conversations, case-insensitively, and only mine
    And "%" and "_" in the search match those characters, never everything
