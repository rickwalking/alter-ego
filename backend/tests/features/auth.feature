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

  # AE-0097 safety-net additions (login JWT shape, logout, change-password guard)

  Scenario: Login response carries the access_token cookie attributes and an HS256 JWT
    Given an admin user exists with a known password
    When I send a POST request to "/api/auth/token" with valid credentials
    Then the response status should be 200
    And the body access_token decodes as an HS256 JWT of type "auth"
    And the access_token cookie is HttpOnly with SameSite=strict and a max-age

  Scenario: Logout clears the access_token cookie
    Given I am authenticated as an admin
    When I send a POST request to "/api/auth/logout"
    Then the response status should be 204
    And the access_token cookie is cleared

  Scenario: Change password rejects a wrong current password
    Given I am authenticated as an editor with a known password
    When I send a POST request to "/api/auth/change-password" with a wrong current password
    Then the response status should be 401

  # DISCOVERED DEFECT (AE-0097, reported — not fixed in this tests-only ticket):
  # change-password reloads the user, sets hashed_password (no updated_at bump),
  # then repo.update's post-flush to_entity() lazy-loads the onupdate-expired
  # updated_at column synchronously inside the async route -> SQLAlchemy 500.
  Scenario: Change password currently 500s due to onupdate lazy-load defect
    Given I am authenticated as an editor with a known password
    When I send a POST request to "/api/auth/change-password" with a valid new password
    Then the response status should currently be 500 (defect baseline locked)
