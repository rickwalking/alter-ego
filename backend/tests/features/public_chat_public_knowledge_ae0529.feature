Feature: Only the site owner, in the site owner's conversations, reads personal knowledge
  As the site owner
  I want my personal knowledge to stay in my own conversations, read only by me
  So that visitors, editors and other admins only ever get what I marked public

  Scenario: An anonymous visitor's chat searches public knowledge only
    Given an anonymous conversation
    When the visitor asks the chat a question
    Then the knowledge search runs on the "public" namespace only

  Scenario: An anonymous visitor's chat lists public documents only
    Given a completed personal document and a completed public document
    When the chat of an anonymous conversation lists the documents
    Then only the public document is listed

  Scenario: The owner's chat reads personal and public knowledge
    Given a conversation of the configured site owner
    When the owner asks the chat a question
    Then the knowledge search covers the "personal" and "public" namespaces
    And the list of documents shows personal and public documents

  Scenario: An editor's or another admin's chat reads public knowledge only
    Given a conversation of a signed-in user who is not the site owner
    When that user asks the chat a question
    Then the knowledge search runs on the "public" namespace only

  Scenario: Without a configured site owner every chat reads public knowledge only
    Given no site owner is configured
    When anyone chats, the owner included
    Then the knowledge search runs on the "public" namespace only

  Scenario: A chat agent built without a knowledge scope reads public knowledge only
    Given a chat agent built without a knowledge scope
    Then it searches the "public" namespace and lists public documents only

  Scenario: An admin posting in the site owner's conversation reads public knowledge only
    Given a conversation of the site owner
    When another admin posts in it
    Then the knowledge search runs on the "public" namespace only

  Scenario: The site owner posting in someone else's conversation reads public knowledge only
    Given the site owner is an admin and an editor's conversation
    When the site owner posts in the editor's conversation
    Then the knowledge search runs on the "public" namespace only

  Scenario: Both chat routes pick the scope from the conversation owner
    Given conversations of the site owner, an editor, another admin and an anonymous visitor
    When each one chats on the streaming route or the messages route
    Then only the site owner calling in the site owner's conversation gets the owner scope

  Scenario: The public scope returns only public knowledge from the index
    Given an index holding one personal chunk and one public chunk
    When the public chat agent searches and lists the knowledge
    Then only the public chunk and the public document come back

  Scenario: A search without a namespace reads public knowledge only
    Given a knowledge search that names no namespace
    Then it reads the "public" namespace only

  Scenario: The knowledge search API reads personal knowledge only for the site owner
    Given the site owner and an editor
    When each one calls the knowledge search API
    Then the owner searches personal and public knowledge and the editor public only

  Scenario: The carousel chat reads personal knowledge only for the site owner
    Given carousel chat agents built for the site owner and for an editor
    Then the owner's agent searches personal and public knowledge and the editor's public only
