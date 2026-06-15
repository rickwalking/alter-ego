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

  # --- AE-0088 safety-net additions (scope / access-control / error paths) ---
  # Scope-specific upload/storage/namespace behavior is covered by
  # tests/features/agent_split/document_scope.feature; the scenarios below
  # capture the /api/documents request/response CONTRACT that the Phase 2
  # Knowledge extraction must preserve byte-for-byte, without duplicating
  # the Pinecone-namespace behavior asserted there.

  Scenario: Create document with explicit personal scope
    Given a valid document payload with scope "personal"
    When I send POST /api/documents with the payload
    Then the response status is 201
    And the response document scope is "personal"
    And the response document is_public is false

  Scenario: Create document with public scope and is_public flag
    Given a valid document payload with scope "public" and is_public true
    When I send POST /api/documents with the payload
    Then the response status is 201
    And the response document scope is "public"
    And the response document is_public is true

  Scenario: Create document with an invalid scope value
    Given a valid document payload with scope "invalid"
    When I send POST /api/documents with the payload
    Then the response status is 400
    And the response contains an error message

  Scenario: Create document defaults to personal scope when scope omitted
    Given a valid document payload with title and content
    When I send POST /api/documents with the payload
    Then the response status is 201
    And the response document scope is "personal"

  Scenario: Listing returns only the caller's own documents (non-admin owner)
    Given a document owned by another user exists
    And a document owned by the caller exists
    When I send GET /api/documents as the owner
    Then the response status is 200
    And the items list contains only the caller's documents

  Scenario: Admin listing returns documents across all owners
    Given a document owned by another user exists
    When I send GET /api/documents as an admin
    Then the response status is 200
    And the items list contains the other user's document

  Scenario: Listing supports limit and offset pagination
    Given multiple documents owned by the caller exist
    When I send GET /api/documents with limit 1 and offset 0
    Then the response status is 200
    And the items list contains at most 1 document
    And the limit field equals 1
    And the offset field equals 0

  Scenario: Listing rejects an out-of-range limit
    When I send GET /api/documents with limit 0
    Then the response status is 422
    And the response contains a validation error

  Scenario: Non-owner cannot read another user's document
    Given a document owned by another user exists
    When the caller sends GET /api/documents/{id} for that document
    Then the response status is 403
    And the response contains an error message

  Scenario: Non-owner cannot read another user's document status
    Given a document owned by another user exists
    When the caller sends GET /api/documents/{id}/status for that document
    Then the response status is 403

  Scenario: Non-owner cannot delete another user's document
    Given a document owned by another user exists
    When the caller sends DELETE /api/documents/{id} for that document
    Then the response status is 403

  Scenario: Non-owner cannot reprocess another user's document
    Given a document owned by another user exists
    When the caller sends POST /api/documents/{id}/reprocess for that document
    Then the response status is 403

  Scenario: Owner can read their own document by ID
    Given a document owned by the caller exists
    When the caller sends GET /api/documents/{id} for that document
    Then the response status is 200
    And the response contains the document with that ID

  Scenario: Get document with a malformed (non-UUID) ID
    When I send GET /api/documents/not-a-uuid
    Then the response status is 422
    And the response contains a validation error

  Scenario: Unauthenticated request to list documents is rejected
    Given no authentication credentials are provided
    When I send GET /api/documents
    Then the response status is 401
