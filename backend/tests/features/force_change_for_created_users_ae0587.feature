Feature: Users an admin creates must change the password at the first sign-in
  An admin who creates a user knows the first password: the API generated it
  and showed it to the admin, or the admin typed it. Like after an admin
  reset, the new user must change it at the first login: until then every
  protected endpoint except me, change-password and logout answers 403 with
  the code password_change_required. Users created any other way (the
  bootstrap owner, the internal user service) are not flagged.

  Scenario: A user created with a generated password must change it
    Given an admin
    When the admin creates a user without a password
    Then the temporary password is returned once
    And the new user must change the password

  Scenario: A user created with a password the admin typed must change it too
    Given an admin
    When the admin creates a user with a password they chose
    Then no temporary password is returned
    And the new user must change the password

  Scenario: A created user is refused on protected endpoints until the change
    Given a user an admin created with a generated password
    When they log in with that password
    Then the login succeeds and me reports must_change_password true
    And a protected endpoint answers 403 with the code password_change_required
    When they change the password
    Then the flag is cleared and the protected endpoint answers 200
    And the generated password no longer logs in

  Scenario: A refused create flags nobody
    Given an admin
    When the admin creates a user with an email that already exists
    Then nothing is written

  Scenario: Users created outside the admin create flow are not flagged
    Given the bootstrap owner script or the internal user service
    When it creates a user
    Then the user is not asked to change the password
