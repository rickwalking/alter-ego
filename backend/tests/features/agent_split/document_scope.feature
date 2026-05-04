Feature: Document Scope and Namespace Management
  As a content manager
  I want to upload documents with different security scopes
  So that the right agent can access the right information

  Background:
    Given an authenticated editor user exists
    And the user is logged in

  Scenario: Upload document with personal scope
    When the user uploads a document with:
      | field   | value                          |
      | title   | Pedro's CV                     |
      | content | Experience: 10 years Python... |
      | scope   | personal                       |
    Then the response status should be 201
    And the document scope should be "personal"
    And the document should be stored in Pinecone namespace "personal"

  Scenario: Upload document with public scope
    When the user uploads a document with:
      | field     | value                          |
      | title     | Blog Post: FastAPI Guide       |
      | content   | FastAPI is a modern web framework... |
      | scope     | public                         |
      | is_public | true                           |
    Then the response status should be 201
    And the document scope should be "public"
    And the document should be stored in Pinecone namespace "public"

  Scenario: Upload document with invalid scope is rejected
    When the user uploads a document with:
      | field   | value        |
      | title   | Test Doc     |
      | content | Some content |
      | scope   | invalid      |
    Then the response status should be 400
    And the error message should mention "Invalid scope"

  Scenario: Document defaults to personal scope when not specified
    When the user uploads a document without specifying scope
    Then the document scope should be "personal"

  Scenario: List documents filters by scope
    Given documents exist with scopes:
      | title        | scope    |
      | Personal Doc | personal |
      | Public Doc   | public   |
      | Internal Doc | internal |
    When the Alter-Ego agent lists available documents
    Then the list should include "Personal Doc"
    And the list should include "Public Doc"
    But the list should NOT include "Internal Doc"

  Scenario: Delete document removes from correct namespace
    Given a document with scope "personal" exists
    When the user deletes the document
    Then the document should be removed from the database
    And the document vectors should be removed from Pinecone namespace "personal"

  Scenario: Reprocess document maintains scope
    Given a document with scope "public" exists and is processed
    When the user reprocesses the document
    Then the new vectors should be stored in Pinecone namespace "public"
    And the old vectors should be removed from Pinecone namespace "public"

  Scenario: Search across namespaces with prefix filter
    Given documents exist:
      | title          | scope    |
      | CV Document    | personal |
      | Blog Article   | public   |
      | Template Guide | internal |
    When searching with namespace_prefix "personal"
    Then results should include "CV Document"
    And results should NOT include "Blog Article"
    And results should NOT include "Template Guide"

  Scenario: Anonymous user can query public documents via chat
    Given a document with scope "public" exists with content "Pedro wrote about FastAPI"
    When an anonymous user asks "What did Pedro write about?"
    Then the response should mention "FastAPI"
    And the response should cite the public document

  Scenario: Anonymous user cannot query personal documents directly
    Given a document with scope "personal" exists with content "Pedro's salary is confidential"
    When an anonymous user asks "What is Pedro's salary?"
    Then the response should NOT contain "confidential"
    Or the response should indicate no information was found
