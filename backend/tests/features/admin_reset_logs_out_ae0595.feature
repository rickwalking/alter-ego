Feature: An admin password reset logs out every open session of the user
  When an admin resets a user's password, the user's token version is bumped
  in the same write as the new temporary hash, so every access token issued to
  that user before the reset is refused with 401, like an expired token. The
  user signs in again with the temporary password and must change it. The
  admin's own session is not touched, because the admin resets somebody else.
  The reset reads the user row locked, like a password change, so a reset and a
  change racing on the same user each bump the version once.

  Scenario: An admin reset bumps the token version in the same write
    Given a user whose token version is 2
    When an admin resets their password
    Then the temporary hash is stored, the token version is 3 and must_change_password is set
    And it is committed once, from the user row read locked

  Scenario: An admin reset logs out every open session of the user
    Given a user signed in on a session
    When an admin resets their password
    Then that session's token is refused with 401 on me
    And it is refused with 401 on change-password
    And it is refused with 401 on a protected endpoint

  Scenario: The temporary password signs in and must be changed
    Given an admin reset a user's password
    When the user signs in with the temporary password
    Then the sign-in succeeds and me reports that the password must change
    And a protected endpoint answers 403 password_change_required
    And changing the password from the temporary one succeeds

  Scenario: The admin's session survives the reset of another user
    Given an admin signed in on a session
    When the admin resets another user's password
    Then the admin's session keeps working on me and on the admin users list
    And the admin's token version is unchanged

  Scenario: An admin who resets their own password is logged out too
    Given an admin signed in on a session
    When the admin resets their own password through the admin endpoint
    Then the admin's token version is bumped and that session is refused with 401 on me
    And the admin signs in again with the temporary password

  Scenario: A reset of an unknown user changes no token version
    Given a signed-in admin and another user
    When the admin resets the password of a user that does not exist
    Then the answer is 404 and no user's token version changes

  Scenario: A reset by a user who is not an admin changes no token version
    Given an editor signed in on a session and another user
    When the editor tries to reset the other user's password
    Then the answer is 403 and no user's token version changes
    And the other user's session keeps working

  Scenario: A reset waits for a password change that holds the user row
    Given a password change that holds the user row lock
    When an admin resets the user's password meanwhile
    Then the reset waits on the lock and the stored version stays unchanged
    And once the change commits the reset bumps from it, so the token version ends two higher
