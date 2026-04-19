Feature: Document Management

  As a user
  I want to manage documents in the knowledge base
  So that the AI can reference my content

  Scenario: Create document with valid data
    Given a valid document payload with title and content
    When I send POST /api/documents with the payload
    Then the response status is 201
    And the response contains the document with status "pending"
    And the document has a unique ID

  Scenario: Create document with missing title
    Given a document payload without a title
    When I send POST /api/documents with the payload
    Then the response status is 422
    And the response contains a validation error

  Scenario: Create document with missing content
    Given a document payload without content
    When I send POST /api/documents with the payload
    Then the response status is 422
    And the response contains a validation error

  Scenario: Create document with empty title
    Given a document payload with an empty title
    When I send POST /api/documents with the payload
    Then the response status is 422
    And the response contains a validation error

  Scenario: List documents when none exist
    Given no documents in the database
    When I send GET /api/documents
    Then the response status is 200
    And the items list is empty
    And the total count is 0

  Scenario: List documents with existing documents
    Given at least one document exists in the database
    When I send GET /api/documents
    Then the response status is 200
    And the items list contains at least one document
    And the total count is greater than 0

  Scenario: Get document by existing ID
    Given a document exists with ID "doc-123"
    When I send GET /api/documents/doc-123
    Then the response status is 200
    And the response contains the document with ID "doc-123"

  Scenario: Get document by non-existing ID
    Given no document exists with ID "nonexistent"
    When I send GET /api/documents/nonexistent
    Then the response status is 404
    And the response contains an error message

  Scenario: Delete existing document
    Given a document exists with ID "doc-123"
    When I send DELETE /api/documents/doc-123
    Then the response status is 204
    And the document is no longer retrievable

  Scenario: Delete non-existing document
    Given no document exists with ID "nonexistent"
    When I send DELETE /api/documents/nonexistent
    Then the response status is 404
    And the response contains an error message

  Scenario: Upload valid text file
    Given a valid .txt file with content
    When I send POST /api/documents/upload with the file
    Then the response status is 201
    And the document is created with the file name as title

  Scenario: Upload empty file
    Given an empty file with no content
    When I send POST /api/documents/upload with the file
    Then the response status is 400
    And the response contains an error message

  Scenario: Reprocess existing document
    Given a document exists with ID "doc-123" in "pending" status
    When I send POST /api/documents/doc-123/reprocess
    Then the response status is 200
    And the document status is updated

  Scenario: Reprocess non-existing document
    Given no document exists with ID "nonexistent"
    When I send POST /api/documents/nonexistent/reprocess
    Then the response status is 404
    And the response contains an error message

  Scenario: Get document status for existing document
    Given a document exists with ID "doc-123"
    When I send GET /api/documents/doc-123/status
    Then the response status is 200
    And the response contains the document status

  Scenario: Get document status for non-existing document
    Given no document exists with ID "nonexistent"
    When I send GET /api/documents/nonexistent/status
    Then the response status is 404
    And the response contains an error message
