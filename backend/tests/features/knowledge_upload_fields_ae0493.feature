Feature: A knowledge upload keeps the title and tags typed in the form
  As the site owner
  I want the title and tags I type when uploading a document to be saved
  So that I can find the document by the name and tags I chose

  Scenario: The typed title and tags are saved
    Given the upload form sends a file with the title "Meu currículo" and the tags "cv, carreira , "
    When the document is uploaded
    Then the ingested document is titled "Meu currículo"
    And its metadata tags are "cv,carreira"

  Scenario: Without a title the file name is used
    Given the upload form sends only a file named "notes.txt"
    When the document is uploaded
    Then the ingested document is titled "notes.txt"
    And its metadata has no tags

  Scenario: The scope and public flag come from the same form
    Given the upload form sends the scope "public" and is_public "true"
    When the document is uploaded
    Then the ingested document has the public scope and is public

  Scenario: An unknown scope is still rejected
    Given the upload form sends the scope "everyone"
    When the document is uploaded
    Then the upload is refused with 400

  Scenario: An anonymous upload is refused
    Given a visitor who is not signed in
    When they upload a file with a title and tags
    Then the upload is refused with 401 and nothing is ingested

  Scenario: A title longer than 500 characters is refused
    Given the upload form sends a title of 501 characters
    When the document is uploaded
    Then the upload is refused with 422 and nothing is ingested

  Scenario: A scope longer than 20 characters is refused
    Given the upload form sends a scope of 21 characters
    When the document is uploaded
    Then the upload is refused with 422 and nothing is ingested
    But a scope of 20 characters passes the length check and reaches the scope validation

  Scenario: Over-long tags are refused
    Given the upload form sends tags longer than 1000 characters
    When the document is uploaded
    Then the upload is refused with 422 and nothing is ingested
