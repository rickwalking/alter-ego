Feature: The Knowledge Base shows my carousels' sources
  As the site owner looking at my knowledge base
  I want a read-only tab with the sources of my carousels
  So that I can see which sources fed which carousel and open it

  Scenario: The Documents tab is the default and is unchanged
    When I open the knowledge base
    Then the "Documentos" tab is selected and lists my documents

  Scenario: The carousel sources tab lists each source with its carousel
    Given my carousels have content sources
    When I open the "Fontes dos carrosséis" tab
    Then each source shows its title, type and date
    And a link to its carousel
    And a URL source links to its URL

  Scenario: The carousel sources paginate
    Given more sources than one page
    When I go to the next page
    Then the next page is requested and the range "21–25 de 25" is shown
    And I can go back to the previous page

  Scenario: The carousel sources can be filtered by carousel
    Given sources on two carousels
    When I choose one carousel in the filter
    Then only that carousel's sources are requested from the first page

  Scenario: No carousel sources shows an empty state
    Given my carousels have no content sources
    When I open the "Fontes dos carrosséis" tab
    Then it says there are no carousel sources yet

  Scenario: A failed load says so
    Given the carousel sources cannot be loaded
    When I open the "Fontes dos carrosséis" tab
    Then it says the sources could not be loaded
