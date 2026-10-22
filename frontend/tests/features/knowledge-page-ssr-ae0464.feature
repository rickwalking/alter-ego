Feature: Knowledge base page renders without a server error
  As the site owner opening the knowledge base
  I want the page to load without a server-side render error and with one page heading
  So that the console stays clean and screen readers announce the page once

  Scenario: The server render shows the list skeleton without calling the API
    Given the knowledge page is rendered on the server
    When the HTML is produced
    Then the documents API is not called and the list skeleton is shown

  Scenario: The browser loads the documents after hydration
    Given the knowledge page is open in the browser
    When the documents load
    Then the document list is shown

  Scenario: The page has a single heading
    Given the knowledge page is open
    Then there is exactly one level-1 heading, "Knowledge Base"
