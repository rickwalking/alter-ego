Feature: The owner changes a knowledge document's scope
  As the site owner
  I want to move a document between my personal and my public knowledge
  So that the scope I see in the Knowledge Base is where its chunks are indexed

  Scenario: Making a personal document public re-indexes it in the public namespace
    Given a completed personal document of mine
    When I change its scope to "public"
    Then its chunks are deleted from the "personal" namespace
    And it is re-indexed in the "public" namespace
    And the document comes back with the scope "public" and is public

  Scenario: Making a public document personal re-indexes it in the personal namespace
    Given a completed public document of mine
    When I change its scope to "personal"
    Then its chunks are deleted from the "public" namespace
    And it is re-indexed in the "personal" namespace
    And the document comes back with the scope "personal" and is not public

  Scenario: The same scope changes nothing
    Given a completed personal document of mine
    When I change its scope to "personal"
    Then the document is returned unchanged and nothing is re-indexed

  Scenario: Only the personal and public scopes can be chosen
    Given a completed personal document of mine
    When I change its scope to "carousel"
    Then the change is refused with 400 and nothing is re-indexed

  Scenario: A document of someone else cannot be rescoped
    Given a completed personal document of another editor
    When I change its scope to "public"
    Then the change is refused with 403 and nothing is re-indexed

  Scenario: An admin can rescope any document
    Given a completed personal document of another editor
    When an admin changes its scope to "public"
    Then the document comes back with the scope "public" and is public

  Scenario: An unknown document cannot be rescoped
    When I change the scope of a document that does not exist
    Then the change is refused with 404

  Scenario: An anonymous visitor cannot rescope a document
    Given a completed personal document of mine
    When a visitor who is not signed in changes its scope
    Then the change is refused with 401 and nothing is re-indexed

  Scenario: A failed re-index after a scope change is saved as failed
    Given a completed personal document of mine
    And the embedding service is unavailable
    When I change its scope to "public"
    Then the document keeps the scope "public" and is saved as failed with the reason
