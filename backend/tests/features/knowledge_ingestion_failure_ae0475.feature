Feature: Knowledge processing failures are recorded, never lost
  As the site owner
  I want a document whose processing fails to stay marked as failed with the reason
  So that it never sits "pending" forever and I can retry it

  Scenario: A failed reprocess is saved as failed with the reason
    Given a stored document whose processing fails with "embedding service unavailable"
    When the document is reprocessed
    Then the response reports status "failed" with that reason
    And reading the document again shows status "failed" with that reason

  Scenario: A successful reprocess clears an earlier failure
    Given a stored document marked failed
    When the document is reprocessed successfully
    Then it is "completed" with its chunk count and no error

  Scenario: The failure reason is short and names the error type
    Given processing fails with a very long error message
    When the failure is recorded
    Then the reason starts with the error type and is at most 300 characters

  Scenario: An upload whose processing fails still rolls back
    Given an uploaded file whose processing fails
    When it is ingested
    Then the error propagates and nothing is persisted
