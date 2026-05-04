Feature: Admin User Management

  Scenario: Admin creates a new user with auto-generated password
    Given I am authenticated as an admin
    When I send a POST request to "/api/admin/users" with:
      | email     | neweditor@test.com |
      | full_name | New Editor         |
      | role      | editor             |
    Then the response status should be 201
    And the response should contain a temporary password
    And the user "neweditor@test.com" should exist with role "editor"

  Scenario: Admin creates user with specific password
    Given I am authenticated as an admin
    When I send a POST request to "/api/admin/users" with:
      | email     | custom@test.com  |
      | full_name | Custom User      |
      | role      | editor           |
      | password  | MyCustomPass123! |
    Then the response status should be 201
    And the response should not contain a temporary password

  Scenario: Admin updates user role
    Given I am authenticated as an admin
    And a user exists with email "target@test.com" and role "editor"
    When I send a PATCH request to "/api/admin/users/{id}" with:
      | role | admin |
    Then the response status should be 200
    And the user role should be "admin"

  Scenario: Admin cannot demote last admin
    Given I am authenticated as the only admin
    When I send a PATCH request to my own user with:
      | role | editor |
    Then the response status should be 409

  Scenario: Admin deletes a user
    Given I am authenticated as an admin
    And a user exists with email "delete_me@test.com"
    When I send a DELETE request to "/api/admin/users/{id}"
    Then the response status should be 204
    And the user should no longer exist

  Scenario: Admin cannot delete themselves
    Given I am authenticated as an admin
    When I send a DELETE request to my own user id
    Then the response status should be 409

  Scenario: Admin cannot delete last admin
    Given I am authenticated as the only admin
    When I send a DELETE request to my own user id
    Then the response status should be 409

  Scenario: Admin resets user password
    Given I am authenticated as an admin
    And a user exists with email "reset_me@test.com"
    When I send a POST request to "/api/admin/users/{id}/reset-password"
    Then the response status should be 200
    And the response should contain a new temporary password
    And the old password should no longer work
