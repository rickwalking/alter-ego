Feature: A rolled-back scope change or reprocess leaves the document retryable
  As the site owner
  I want a document whose re-index was rolled back to show as failed
  So that I can retry it instead of trusting a completed document with no chunks

  Scenario: A failed save after a scope change marks the document failed
    Given a completed personal document of mine
    When I change its scope to "public" and saving the change fails
    Then the chunks written to the "public" namespace are deleted again
    And the document is saved as failed with the processing error, so Retry shows
    And the request fails with the saving error

  Scenario: A failed save after a reprocess marks the document failed
    Given a completed document of mine
    When I reprocess it and saving the result fails
    Then the document is saved as failed with the processing error
    And the request fails with the saving error

  Scenario: A failing cleanup never hides the original error
    Given a scope change whose save failed
    When deleting the new namespace's chunks or marking the document failed also fails
    Then that failure is logged
    And the request fails with the original saving error

  Scenario: The system scope check runs under the row lock
    Given a document in the "carousel" scope
    When I change its scope to "public"
    Then the document row is locked before its scope is checked
    And the change is refused as a system scope without touching any chunks
