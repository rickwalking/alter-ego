Feature: Hybrid Search

  As a user
  I want to search the knowledge base
  So that I can find relevant documents

  Scenario: Search with valid query
    Given documents exist in the knowledge base
    When I send POST /api/search with query "artificial intelligence"
    Then the response status is 200
    And the response contains search results

  Scenario: Search with empty query
    Given any state of the knowledge base
    When I send POST /api/search with an empty query
    Then the response status is 422
    And the response contains a validation error

  Scenario: Search with custom top_k
    Given documents exist in the knowledge base
    When I send POST /api/search with query "test" and top_k 3
    Then the response status is 200
    And the results contain at most 3 items

  Scenario: Search with custom alpha
    Given documents exist in the knowledge base
    When I send POST /api/search with query "test" and alpha 0.8
    Then the response status is 200
    And the response contains search results

  Scenario: Search with invalid alpha (negative)
    Given any state of the knowledge base
    When I send POST /api/search with query "test" and alpha -0.1
    Then the response status is 422
    And the response contains a validation error

  Scenario: Search with invalid alpha (greater than 1)
    Given any state of the knowledge base
    When I send POST /api/search with query "test" and alpha 1.5
    Then the response status is 422
    And the response contains a validation error

  Scenario: Search via GET with valid query
    Given documents exist in the knowledge base
    When I send GET /api/search with query "test"
    Then the response status is 200
    And the response contains search results

  Scenario: Search via GET with empty query
    Given any state of the knowledge base
    When I send GET /api/search with an empty query
    Then the response status is 422
    And the response contains a validation error

  Scenario: Search with invalid top_k (zero)
    Given any state of the knowledge base
    When I send POST /api/search with query "test" and top_k 0
    Then the response status is 422
    And the response contains a validation error

  Scenario: Search with invalid top_k (negative)
    Given any state of the knowledge base
    When I send POST /api/search with query "test" and top_k -1
    Then the response status is 422
    And the response contains a validation error

  Scenario: Search with invalid top_k (too large)
    Given any state of the knowledge base
    When I send POST /api/search with query "test" and top_k 101
    Then the response status is 422
    And the response contains a validation error
