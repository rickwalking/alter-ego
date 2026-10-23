Feature: Retry and delete clear a document's chunks from both selectable scopes
  As the site owner
  I want no chunk of a document to linger in the scope it never got
  So that a failed scope change can never leave personal knowledge in the public namespace

  Scenario: Retry after a failed scope change clears the other scope's namespace
    Given a personal document whose move to public failed after indexing, and whose cleanup failed too
    When I retry the document
    Then none of its chunks are left in the "public" namespace
    And it is indexed again in the "personal" namespace

  Scenario: Deleting a document clears both selectable namespaces
    Given a personal document with chunks left in the "public" namespace
    When I delete the document
    Then none of its chunks are left in either namespace
