Feature: The create-user password is masked

  An admin creating a user may type the new user's password. It must never
  be shown on screen unless the admin asks to see it, and browsers must treat
  it as a new password rather than autofilling the admin's own.

  Scenario: The create-user password is masked by default
    Given the admin opens the "Criar usuário" dialog
    When they look at the password field
    Then it is a password input with autocomplete "new-password"
    And its show/hide toggle is a button labelled "Show password"

  Scenario: The admin can show and hide the typed password
    Given the admin typed a password in the "Criar usuário" dialog
    When they press "Show password"
    Then the password is shown as text and the toggle reads "Hide password"
    When they press "Hide password"
    Then the password is masked again

  Scenario: A typed password is never echoed back
    Given the admin typed a password and created the user
    When the API confirms the user was created
    Then the success message does not contain the typed password
