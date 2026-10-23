Feature: Conversations are titled from their first message
  As a signed-in user browsing my chat history
  I want each conversation named after what I asked
  So that I can find it again instead of a list of "New conversation"

  Scenario: The first message titles an untitled conversation
    Given an untitled conversation
    When I send "What do you think about microservices?"
    Then the conversation is titled "What do you think about microservices?"

  Scenario: A long or multi-line first message gives a short one-line title
    When the first message is longer than 60 characters or spans several lines
    Then the title is its first line, cut at 60 characters with an ellipsis
    And a message of exactly 60 characters is kept whole
    And no space is left before the ellipsis

  Scenario: An existing title is never replaced
    Given a conversation already has a title
    When I send another message
    Then the title stays the same
    And a blank message never titles a conversation
