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
