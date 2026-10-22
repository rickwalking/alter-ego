Feature: Saving a user's new password

  Admin password reset and self-service change-password only change the
  password hash. The repository must save that change and return the user
  without lazy-loading a database-set column inside the async session.

  Scenario: A password-only update is saved and returned on Postgres
    Given a user stored in Postgres
    When only the user's hashed password changes and the repository updates the user
    Then the returned user carries the new hash and the database-set updated_at
    And reloading the user shows the same hash and updated_at

  Scenario: An update keeps an explicitly bumped updated_at
    Given a user stored in Postgres
    When the user's role changes with an explicit updated_at and the repository updates the user
    Then the stored user has the new role and exactly that updated_at
