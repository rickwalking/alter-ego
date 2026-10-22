Feature: Knowledge documents show their processing state and can be retried
  As the site owner looking at my knowledge base
  I want to see whether each document was processed, why it failed, and retry it
  So that a document never sits "pending · 0 chunks" without explanation

  Scenario: A failed document shows its reason and a Retry button
    Given a document whose processing failed with the reason "embedding_unavailable"
    Then its card shows the failed state, the reason in words and a "Retry" button
    And clicking "Retry" reprocesses the document

  Scenario: A document stuck in processing is shown as stale with Retry
    Given a document still "pending" or "processing" more than 10 minutes after its last update
    Then its card says processing did not finish and offers "Retry"

  Scenario: A fresh or completed document offers no Retry
    Given a document that is completed, or pending for less than 10 minutes
    Then its card offers no "Retry"

  Scenario: Status and labels are translated
    Given the interface is in Portuguese
    Then the status, the chunk count and the delete label are in Portuguese

  Scenario: A new document is processed right after it is created
    When I create a document with the "New Document" form
    Then its processing starts immediately

  Scenario: Each failure reason code is shown in words
    Given a failed document whose reason is "vector_store_unavailable", "empty_content" or "processing_error"
    Then its card explains that reason in words

  Scenario: A saved reason that is not a known code is never shown verbatim
    Given a failed document whose saved reason is free text from an older version
    Then its card shows the generic processing error, not the text

  Scenario: A failed retry says so on its document
    Given I click "Retry" on a document
    When the retry request fails
    Then that document's card shows that the retry could not start
    And its "Retry" button is enabled again

  Scenario: Retrying two documents keeps each one busy until its own retry ends
    Given I click "Retry" on document A and then on document B
    When B's retry finishes first
    Then A still shows that it is retrying until its own retry ends
