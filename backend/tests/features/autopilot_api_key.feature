Feature: Autopilot service API key
  The host scout calls /api/autopilot/* with X-Api-Key.
  The key is checked as a sha256 hex digest. It never grants a user identity.

  Scenario: Valid key accesses autopilot routes
    Given the server is configured with the sha256 of key "k1"
    When the scout calls GET /api/autopilot/signals with X-Api-Key "k1"
    Then the response status is 200

  Scenario: Wrong key is rejected
    Given the server is configured with the sha256 of key "k1"
    When the scout calls GET /api/autopilot/signals with X-Api-Key "nope"
    Then the response status is 401
    And a warning is logged that does not contain the key

  Scenario: Missing key is rejected
    Given the server is configured with the sha256 of key "k1"
    When the scout calls GET /api/autopilot/signals without X-Api-Key
    Then the response status is 401
    And a warning is logged that does not contain the key

  # GET /api/carousels (the list) is anonymous-public and stays 200.
  # A route that already requires a user still returns 401 when only the
  # service key is sent. GET /api/carousels/{project_id} is the protected
  # route under that prefix.
  Scenario: Key does not unlock other routes
    Given the server is configured with the sha256 of key "k1"
    When the scout calls GET /api/documents with X-Api-Key "k1"
    And the scout calls GET /api/carousels/{project_id} with X-Api-Key "k1"
    Then each response status is 401

  Scenario: API key is ignored on the public carousel list
    Given the server is configured with the sha256 of key "k1"
    When the scout calls GET /api/carousels with X-Api-Key "k1"
    Then the response status matches a call with no API key and no user token

  Scenario: Feature disabled
    Given no autopilot key hash is configured
    When the scout calls GET /api/autopilot/signals with X-Api-Key "k1"
    Then the response status is 503

  Scenario: Autopilot routes share a per-IP rate limit
    Given the server is configured with the sha256 of key "k1"
    When the scout calls GET /api/autopilot/signals with X-Api-Key "k1" more than 10 times in a minute
    Then the response status is 429

  Scenario: The API key dependency is only on autopilot routes
    When the application routes are inspected
    Then require_autopilot_api_key is present on every /api/autopilot route
    And it is absent from every other route
