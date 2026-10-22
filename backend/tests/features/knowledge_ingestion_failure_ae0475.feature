Feature: Knowledge processing failures are recorded, never lost
  As the site owner
  I want a document whose processing fails to stay marked as failed with the reason
  So that it never sits "pending" forever and I can retry it

  Scenario: A failed reprocess is saved as failed with the reason
    Given a stored document whose embedding step fails
    When the document is reprocessed
    Then the response reports status "failed" with the reason "embedding_unavailable"
    And reading the document again shows status "failed" with that reason

  Scenario: A successful reprocess clears an earlier failure
    Given a stored document marked failed
    When the document is reprocessed successfully
    Then it is "completed" with its chunk count and no error

  Scenario: The saved reason never carries the error text
    Given the embedding step fails with a message holding a host, a URL and a key fragment
    When the failure is recorded
    Then the saved reason is "embedding_unavailable"
    And none of the message text is saved or returned

  Scenario: A vector store failure is saved as vector store unavailable
    Given a stored document whose vector store upsert fails
    When the document is reprocessed
    Then it is "failed" with the reason "vector_store_unavailable"

  Scenario: A document without content is saved as empty content
    Given a stored document that produces no chunks
    When the document is reprocessed
    Then it is "failed" with the reason "empty_content"

  Scenario: Any other failure is saved as a processing error
    Given a stored document whose status update fails
    When the document is reprocessed
    Then it is "failed" with the reason "processing_error"

  Scenario: An upload whose processing fails still rolls back
    Given an uploaded file whose processing fails
    When it is ingested
    Then the error propagates and nothing is persisted
