Feature: A password change logs out every other session of the user
  When a user changes their own password, every access token issued to them
  before the change stops working, so a session somebody else opened with the
  old password is signed out. The session that made the change gets a fresh
  token in the access_token cookie and stays signed in. Each user has a token
  version; an access token carries the version it was issued with (claim tv)
  and is refused with 401, like an expired token, once the user's version has
  moved on. A token issued before versions existed has no tv and counts as
  version 0, so nobody is logged out by the deploy itself.

  Scenario: A new token carries the user's current token version
    Given a user whose token version is 3
    When an access token is issued for them
    Then its tv claim is 3

  Scenario: A password change bumps the token version in the same write
    Given a signed-in user
    When they change the password with the right current password
    Then the new hash is stored, the token version is one higher and must_change_password is cleared

  Scenario: The session that changed the password stays signed in
    Given a user signed in on two sessions
    When the user changes the password on the first session
    Then the answer sets a fresh access_token cookie with the same flags and lifetime as the login
    And the first session keeps working with that cookie

  Scenario: Every other session is logged out by a password change
    Given a user signed in on two sessions
    When the user changes the password on the first session
    Then the second session's token is refused with 401 on a protected endpoint
    And it is refused with 401 on me
    And it is refused with 401 on an editor or admin endpoint
    And an endpoint open to visitors treats it as a visitor

  Scenario: A token without a token version still works for a user at version 0
    Given a user whose token version is 0
    And an access token issued before token versions existed, with no tv claim
    When it is sent to a protected endpoint
    Then it is accepted

  Scenario: A token without a token version is refused once the user changed the password
    Given a user whose token version is 1
    And an access token with no tv claim
    When it is sent to a protected endpoint
    Then it is refused with 401

  Scenario: A token whose tv is not a whole number is refused
    Given a user whose token version is 0
    And an access token whose tv claim is text
    When it is sent to a protected endpoint
    Then it is refused with 401

  Scenario: A wrong current password does not log anyone out
    Given a user signed in on two sessions
    When the user tries to change the password with a wrong current password
    Then the change is refused with 401 and the token version is unchanged
    And no new cookie is set
    And both sessions keep working

  Scenario: Reusing the current password does not log anyone out
    Given a signed-in user
    When they try to change the password to the current one
    Then the change is refused with 400 and the token version is unchanged

  Scenario: Every route that reads the token checks the token version
    Given the real app
    Then every HTTP and websocket route that reads the access token goes through a dependency that checks the token version

  Scenario: An older write never lowers the token version
    Given a user whose token version moved to 2
    When an update carrying the version 1 it read earlier is saved
    Then the stored token version stays 2

  Scenario: The token version column is added on prod by a one-shot
    Given an existing users table without token_version
    When the column one-shot runs with apply and verify
    Then the column exists as INTEGER NOT NULL DEFAULT 0 and existing users read 0
    And a second run is a no-op

  Scenario: Verify fails while token_version is missing
    Given an existing users table without token_version
    When the column one-shot runs with verify only
    Then it exits 1 and reports the column missing

  Scenario: The token version one-shot leaves other databases alone
    Given a database without a users table, or a database that is not Postgres
    When the column one-shot runs with apply and verify
    Then it changes nothing and exits 0

  Scenario: The token version one-shot matches the ORM column
    Given the users model
    Then its token_version column is a NOT NULL integer with a server default of 0
    And the one-shot needs a mode to run

  Scenario: The deploy runs the token version one-shot before the stack comes up
    Given the deploy workflow
    Then the token version one-shot runs after the must_change_password step and before the stack comes up
    And its failure is captured, the stack stays up, and the job fails at the end

  Scenario: The deploy retries a failed token version one-shot in the running backend
    Given the deploy workflow
    When the token version one-shot failed before the stack came up
    Then it runs once more in the running backend before the drift check
    And a successful retry clears the failure, while a second failure still fails the job at the end
