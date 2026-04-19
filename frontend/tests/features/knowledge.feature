Feature: Knowledge Base Management

  As a user
  I want to manage my documents
  So that the AI has content to reference

  Scenario: Display knowledge base interface
    Given I navigate to the knowledge base page
    Then I see the "Knowledge Base" heading
    And I see the document search input
    And I see the "New Document" button
    And I see the "Upload" button

  Scenario: Search documents
    Given documents exist in the knowledge base
    When I type in the search input
    Then the document list is filtered by the search query

  Scenario: Create a new document
    Given I am on the knowledge base page
    When I click the "New Document" button
    Then I see the document creation form
    When I fill in the title and content
    And I click "Create Document"
    Then the document appears in the list
    And the form is closed

  Scenario: Create document with validation error
    Given I am on the document creation form
    When I leave the title empty
    And I click "Create Document"
    Then I see a validation error

  Scenario: Delete a document
    Given a document exists in the list
    When I click the delete button on the document
    Then the document is removed from the list

  Scenario: Upload a file
    Given I am on the knowledge base page
    When I click the "Upload" button
    Then I see the file upload interface
    And I see the drop zone
    And I see the file input

  Scenario: Document list shows empty state
    Given no documents exist in the knowledge base
    When I am on the knowledge base page
    Then I see the "No documents yet" message

  Scenario: Document list shows loading state
    Given documents are being loaded
    When I am on the knowledge base page
    Then I see skeleton loading placeholders
