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

  # AE-0097 safety-net additions

  Scenario: Admin create rejects an invalid role
    Given I am authenticated as an admin
    When I send a POST request to "/api/admin/users" with role "wizard"
    Then the response status should be 422

  Scenario: Non-admin cannot list users
    Given I am authenticated as an editor
    When I send a GET request to "/api/admin/users"
    Then the response status should be 403

  Scenario: Updating a non-existent user returns 404
    Given I am authenticated as an admin
    When I send a PATCH request to "/api/admin/users/{nonexistent-id}"
    Then the response status should be 404

  # DISCOVERED DEFECT (AE-0097, reported — not fixed in this tests-only ticket):
  # same onupdate lazy-load root cause as change-password — reset-password sets
  # hashed_password without bumping updated_at, so repo.update's post-flush
  # to_entity() lazy-loads the expired column synchronously -> 500.
  Scenario: Reset password currently 500s due to onupdate lazy-load defect
    Given I am authenticated as an admin
    And a user exists to reset
    When I send a POST request to "/api/admin/users/{id}/reset-password"
    Then the response status should currently be 500 (defect baseline locked)
