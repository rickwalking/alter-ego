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

  Scenario: Rescoping one document leaves the other documents of its namespace
    Given two completed personal documents of mine indexed in the "personal" namespace
    When I change the scope of the first one to "public"
    Then the second document's chunks are still in the "personal" namespace
    And only the first document's chunks are in the "public" namespace

  Scenario: Deleting one document leaves the other documents of its namespace
    Given two completed personal documents of mine indexed in the "personal" namespace
    When I delete the first one
    Then the second document's chunks are still in the "personal" namespace

  Scenario: A failed save after the re-index removes the new chunks again
    Given a completed personal document of mine
    When I change its scope to "public" and saving the change fails
    Then the change is not saved
    And the document has no chunks left in the "public" namespace

  Scenario: A system document cannot be rescoped
    Given a completed document of mine in the "carousel" scope
    When I change its scope to "public"
    Then the change is refused with 409 and nothing is re-indexed

  Scenario: A scope change and a reprocess lock the document row
    Given a completed personal document of mine
    When I change its scope or reprocess it
    Then the document row is read for update before its chunks are touched
