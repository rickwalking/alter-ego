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

  # --- AE-0088 safety-net additions (response shape / bounds / auth) ---
  # These capture the /api/search request/response CONTRACT (status + JSON
  # shape) the Phase 2 Knowledge extraction must preserve byte-for-byte.

  Scenario: Successful POST search returns the response contract shape
    Given the retriever returns ranked results
    When I send POST /api/search with query "artificial intelligence"
    Then the response status is 200
    And the response echoes the query
    And the response contains a results list
    And each result has content, document_id, document_title, score and rank
    And the response total equals the number of results

  Scenario: Successful GET search returns the response contract shape
    Given the retriever returns ranked results
    When I send GET /api/search with query "test"
    Then the response status is 200
    And the response echoes the query
    And the response contains a results list

  Scenario: POST search at the top_k boundary is accepted
    Given the retriever returns ranked results
    When I send POST /api/search with query "test" and top_k 20
    Then the response status is 200
    And the response contains search results

  Scenario: POST search at the alpha boundaries is accepted
    Given the retriever returns ranked results
    When I send POST /api/search with query "test" and alpha 0.0
    Then the response status is 200
    When I send POST /api/search with query "test" and alpha 1.0
    Then the response status is 200

  Scenario: POST search rejects a query over the maximum length
    Given any state of the knowledge base
    When I send POST /api/search with a query longer than 1000 characters
    Then the response status is 422
    And the response contains a validation error

  Scenario: GET search rejects out-of-range top_k
    Given any state of the knowledge base
    When I send GET /api/search with query "test" and top_k 21
    Then the response status is 422
    And the response contains a validation error

  Scenario: GET search rejects out-of-range alpha
    Given any state of the knowledge base
    When I send GET /api/search with query "test" and alpha 1.5
    Then the response status is 422
    And the response contains a validation error

  Scenario: Unauthenticated POST search is rejected
    Given no authentication credentials are provided
    When I send POST /api/search with query "test"
    Then the response status is 401

  Scenario: Unauthenticated GET search is rejected
    Given no authentication credentials are provided
    When I send GET /api/search with query "test"
    Then the response status is 401
