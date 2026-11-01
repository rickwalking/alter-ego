Feature: Users change their own password, and a reset password must be changed
  Any signed-in user can change their own password with the current one. When
  an admin resets another user's password, the temporary password is shown
  once and the user must change it at the next login: until then every
  protected endpoint except me, change-password and logout answers 403 with
  the code password_change_required.

  Scenario: A signed-in user changes their own password
    Given a signed-in user with a known password
    When they change it with the right current password and a valid new one
    Then the response is 204
    And the new password logs in and the old one does not
    And the user is not asked to change the password again

  Scenario: A wrong current password changes nothing
    Given a signed-in user with a known password
    When they change it with a wrong current password
    Then the response is 401 with the code current_password_incorrect
    And the old password still logs in

  Scenario: A new password equal to the current one is refused
    Given a signed-in user with a known password
    When they change it to the same password
    Then the response is 400 with the code password_unchanged
    And the password and the change flag are unchanged

  Scenario: A new password shorter than the policy is refused
    Given a signed-in user with a known password
    When they change it to a password shorter than the minimum length
    Then the response is 422 and the old password still logs in

  Scenario: Changing the password is rate limited like the login
    Given a signed-in user
    When they try to change the password more than five times in a minute
    Then the extra attempts answer 429

  Scenario: An admin reset makes the user change the password at next login
    Given an admin and another user
    When the admin resets the user's password
    Then the temporary password is returned once
    And the user must change the password

  Scenario: A user with a temporary password is refused on protected endpoints
    Given a user whose password was reset by an admin
    When they log in with the temporary password
    Then the login succeeds and me reports must_change_password true
    And a protected endpoint answers 403 with the code password_change_required
    And logout still works

  Scenario: Changing a temporary password clears the flag
    Given a user whose password was reset by an admin
    When they change the temporary password to a new one
    Then me reports must_change_password false
    And the protected endpoint answers normally

  Scenario: A flagged user is treated as anonymous on public endpoints
    Given a user whose password was reset by an admin
    When an endpoint that accepts an optional user is called with their session
    Then the call is made as an anonymous visitor

  Scenario: The full reset and change flow on Postgres
    Given an admin and an editor stored in Postgres
    When the admin resets the editor's password
    And the editor logs in with the temporary password
    Then a protected endpoint is refused with password_change_required
    When the editor changes the temporary password
    Then the flag is cleared in the database and the protected endpoint answers 200

  Scenario: A wrong current password on Postgres leaves the user unchanged
    Given an editor stored in Postgres with a known password
    When the editor changes the password with a wrong current password
    Then the response is 401 and the stored hash and flag are unchanged

  Scenario: The must_change_password column is added once
    Given a Postgres users table without must_change_password
    When the column one-shot runs with --apply --verify
    Then must_change_password exists as a not null boolean defaulting to false
    And existing users keep their data with the flag false
    And the command exits 0

  Scenario: A second must_change_password run changes nothing
    Given the users table already has must_change_password
    When the column one-shot runs with --apply again
    Then it reports nothing was added

  Scenario: Verify fails while must_change_password is missing
    Given a Postgres users table without must_change_password
    When the column one-shot runs with --verify only
    Then the command exits 1 and names the missing column

  Scenario: A database without the users table is left alone by the column one-shot
    Given a Postgres database without a users table
    When the column one-shot runs with --apply --verify
    Then it reports there is no table yet and exits 0

  Scenario: The must_change_password one-shot is a no-op outside Postgres
    Given a SQLite database
    When the column one-shot runs with --apply --verify
    Then it reports there is nothing to do and exits 0

  Scenario: The must_change_password command needs a mode
    When the column one-shot runs without --apply or --verify
    Then it exits 2 with a usage error

  Scenario: The column one-shot matches the ORM column
    Given the users ORM model
    Then must_change_password is a not null boolean with a false server default

  Scenario: The deploy adds must_change_password before the stack comes up
    Given the deploy workflow
    Then the column one-shot runs after the insight columns step and before the stack comes up
    And its failure is captured, the stack stays up, and the job fails at the end
