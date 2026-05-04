Feature: Authentication

  Scenario: Successful login returns JWT cookie
    Given an admin user exists with email "admin@test.com" and password "SecurePass123!"
    When I send a POST request to "/api/auth/token" with:
      | email    | admin@test.com |
      | password | SecurePass123! |
    Then the response status should be 200
    And the response should set an "access_token" HttpOnly cookie

  Scenario: Invalid credentials are rejected
    When I send a POST request to "/api/auth/token" with:
      | email    | admin@test.com |
      | password | wrongpassword  |
    Then the response status should be 401

  Scenario: Accessing a protected endpoint without a token fails
    When I send a GET request to "/api/documents" without authentication
    Then the response status should be 401

  Scenario: Get current user information
    Given I am authenticated as "admin@test.com"
    When I send a GET request to "/api/auth/me"
    Then the response status should be 200
    And the response should contain email "admin@test.com"
    And the response should contain role "admin"

  Scenario: Change own password
    Given I am authenticated as "editor@test.com" with password "OldPass123!"
    When I send a POST request to "/api/auth/change-password" with:
      | current_password | OldPass123!     |
      | new_password     | NewSecurePass456! |
    Then the response status should be 204
    And I should be able to log in with "NewSecurePass456!"
