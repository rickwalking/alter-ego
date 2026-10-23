Feature: Knowledge documents show and set their scope
  As the site owner looking at my knowledge base
  I want to see and choose whether each document is personal or public
  So that I know which of my knowledge is public and can change it

  Scenario: Each document shows its scope
    Given a personal document and a public document
    Then the first card shows "Pessoal" and the second shows "Público"

  Scenario: An upload is personal unless I choose public
    Given the upload form with a file
    When I upload it without changing the scope
    Then the upload sends the scope "personal" and is_public "false"
    When I choose "Público" and upload it
    Then the upload sends the scope "public" and is_public "true"

  Scenario: A typed document takes the chosen scope
    Given the new document form
    When I choose "Público" and create the document
    Then the create request carries the scope "public" and is_public true

  Scenario: The list can show only public or only personal knowledge
    Given a personal document and a public document
    When I filter by "Público"
    Then only the public document is listed
    When I filter by "Pessoal"
    Then only the personal document is listed
    When I filter by "Todos"
    Then both documents are listed

  Scenario: The scope filter combines with the search
    Given two public documents and one personal document
    When I filter by "Público" and search for the title of one public document
    Then only that document is listed

  Scenario: The owner changes a document's scope from its card
    Given a personal document
    When I choose "Tornar público" on its card
    Then the document's scope change is requested as "public"
    And the card shows the new scope once the server answers

  Scenario: Switching two documents keeps each one busy until its own change ends
    Given two personal documents
    When I switch the scope of the first and then of the second
    Then both switches are disabled
    And the first stays disabled after the second change ends, until its own change ends

  Scenario: A failed scope change says so on its document only
    Given two personal documents whose scope changes are in flight
    When the change of the first fails
    Then only the first card says the change failed

  Scenario: A system document shows its scope without a switch
    Given a document in a system scope such as "internal"
    Then its card shows the badge "Sistema"
    And it has no scope switch
    And it is listed only under "Todos"
