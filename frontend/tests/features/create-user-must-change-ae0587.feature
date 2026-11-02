Feature: The create-user dialog says the new user must change the password
  An admin who creates a user knows the first password, so the API makes the
  new user change it at the first sign-in. The "Criar usuário" dialog says so
  before and after the user is created, in English and Portuguese.

  Scenario: The create-user form says the password must be changed at the first sign-in
    Given the admin opens the "Criar usuário" dialog
    Then it says the new user must change the password at the first sign-in

  Scenario: The result of a create with a generated password repeats the note
    Given the admin created a user without typing a password
    When the API returns the temporary password
    Then the dialog shows the temporary password once
    And it says the user must change it at the first sign-in before using the app

  Scenario: The result of a create with a typed password repeats the note
    Given the admin created a user with a password they typed
    When the API confirms the user was created
    Then the dialog does not echo the typed password
    And it says the user must change it at the first sign-in before using the app
