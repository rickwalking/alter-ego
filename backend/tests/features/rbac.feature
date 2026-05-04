Feature: Role-Based Access Control

  Scenario: Admin can list all users
    Given I am authenticated as an admin
    When I send a GET request to "/api/admin/users"
    Then the response status should be 200
    And the response should contain a list of users

  Scenario: Editor cannot access admin endpoints
    Given I am authenticated as an editor
    When I send a GET request to "/api/admin/users"
    Then the response status should be 403

  Scenario: Visitor cannot upload documents
    When I send a POST request to "/api/documents/upload" without authentication
    Then the response status should be 401

  Scenario: Visitor cannot create carousels
    When I send a POST request to "/api/carousels" without authentication
    Then the response status should be 401

  Scenario: Visitor can read public blog
    Given a carousel project exists with is_public=true
    When I send a GET request to "/api/carousels/{id}/blog" without authentication
    Then the response status should be 200

  Scenario: Editor can delete their own carousel
    Given I am authenticated as an editor
    And I own a carousel project with id "carousel-123"
    When I send a DELETE request to "/api/carousels/carousel-123"
    Then the response status should be 204

  Scenario: Editor cannot delete another user's carousel
    Given I am authenticated as an editor
    And a carousel project exists owned by a different user with id "carousel-456"
    When I send a DELETE request to "/api/carousels/carousel-456"
    Then the response status should be 403

  Scenario: Visitor cannot access search
    When I send a POST request to "/api/search" with body:
      | query | test |
    Then the response status should be 401

  Scenario: Authenticated user can access search
    Given I am authenticated as an editor
    When I send a POST request to "/api/search" with body:
      | query | test |
    Then the response status should be 200
