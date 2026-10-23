Feature: The public chat reads public knowledge only
  As the site owner
  I want anonymous visitors to get answers only from what I marked public
  So that my personal knowledge stays out of the public chat

  Scenario: An anonymous visitor's chat searches public knowledge only
    Given an anonymous conversation
    When the visitor asks the chat a question
    Then the knowledge search runs on the "public" namespace only

  Scenario: An anonymous visitor's chat lists public documents only
    Given a completed personal document and a completed public document
    When the chat of an anonymous conversation lists the documents
    Then only the public document is listed

  Scenario: The owner's chat reads personal and public knowledge
    Given a conversation of a signed-in user
    When the owner asks the chat a question
    Then the knowledge search covers the "personal" and "public" namespaces
    And the list of documents shows personal and public documents

  Scenario: A chat agent built without a knowledge scope reads public knowledge only
    Given a chat agent built without a knowledge scope
    Then it searches the "public" namespace and lists public documents only

  Scenario: Both chat routes pick the scope from the conversation owner
    Given an anonymous conversation and a conversation of a signed-in user
    When each one chats on the streaming route or the messages route
    Then the anonymous one gets the public scope and the signed-in one the owner scope
