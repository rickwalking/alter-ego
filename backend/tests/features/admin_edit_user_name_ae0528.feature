Feature: Admin edits a user's name

  An admin can fix a user's full name through the existing
  PATCH /api/admin/users/{id}. The email stays fixed: the request schema has no
  email field, so a sent email is ignored.

  Scenario: Admin renames a user
    Given I am authenticated as an admin
    And a user exists with the name "Jon Smith"
    When I send a PATCH request to "/api/admin/users/{id}" with full_name "  John Smith  "
    Then the response status should be 200
    And the user's name should be "John Smith"

  Scenario: A blank name is rejected
    Given I am authenticated as an admin
    And a user exists with the name "Jon Smith"
    When I send a PATCH request to "/api/admin/users/{id}" with full_name "   "
    Then the response status should be 422
    And the user's name should still be "Jon Smith"

  Scenario: A name longer than 255 characters is rejected
    Given I am authenticated as an admin
    And a user exists
    When I send a PATCH request with a full_name of 256 characters
    Then the response status should be 422

  Scenario: Omitting the name leaves it unchanged
    Given I am authenticated as an admin
    And a user exists with the name "Jon Smith"
    When I send a PATCH request to "/api/admin/users/{id}" with only role "admin"
    Then the response status should be 200
    And the user's name should still be "Jon Smith"

  Scenario: The email cannot be changed
    Given I am authenticated as an admin
    And a user exists with the email "fixed@example.com"
    When I send a PATCH request with full_name "New Name" and email "other@example.com"
    Then the response status should be 200
    And the user's email should still be "fixed@example.com"

  Scenario: A non-admin cannot rename a user
    Given I am authenticated as an editor
    When I send a PATCH request to "/api/admin/users/{id}" with full_name "Hacker"
    Then the response status should be 403

  Scenario: Renaming an unknown user returns 404
    Given I am authenticated as an admin
    When I send a PATCH request to an unknown user id with full_name "Nobody"
    Then the response status should be 404

  Scenario: The last-admin rule still holds when the name is edited with the role
    Given I am authenticated as the only admin
    When I send a PATCH request to my own user with full_name "Renamed" and role "editor"
    Then the response status should be 409
    And my name should not change
