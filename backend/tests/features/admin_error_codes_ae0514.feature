Feature: Admin and login errors carry a stable code

  The admin user API and the login endpoint keep their HTTP status and their
  English "detail" text, and add a stable "code" so the dashboard can show its
  own Portuguese or English message without matching the English text.

  Scenario: A duplicate email on create returns the email-exists code
    Given I am authenticated as an admin
    And a user exists with the email "taken@example.com"
    When I create a user with the email "taken@example.com"
    Then the response status should be 409
    And the response code should be "user_email_exists"
    And the response detail should still name the email

  Scenario: A deactivated account cannot sign in and gets the inactive code
    Given a deactivated user with a known password
    When that user signs in with the right password
    Then the response status should be 401
    And the response code should be "user_inactive"
    And the response detail should still be "User account is deactivated"

  Scenario: Wrong credentials keep the plain invalid-credentials answer
    Given a user with a known password
    When that user signs in with a wrong password
    Then the response status should be 401
    And the response has no code

  Scenario: Deleting your own account returns the self-delete code
    Given I am authenticated as an admin
    When I delete my own account
    Then the response status should be 409
    And the response code should be "self_delete"

  Scenario: Demoting the last admin returns the last-admin code
    Given I am authenticated as the only admin
    When I change my own role to editor
    Then the response status should be 409
    And the response code should be "last_admin"
