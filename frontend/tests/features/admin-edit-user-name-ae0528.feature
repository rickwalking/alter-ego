Feature: Admin edits a user's name in the edit dialog

  On /admin/users the edit dialog shows a labelled "Nome completo"/"Full name"
  field with the user's current name. The email is shown as fixed text only.

  Scenario: Admin renames a user
    Given the admin opens the edit dialog for "Jon Smith"
    Then the "Full name" field shows "Jon Smith"
    When they change it to "  John Smith  " and save
    Then the PATCH body carries full_name "John Smith"
    And the table is refreshed with the new name

  Scenario: A blank name is rejected before submit
    Given the admin opens the edit dialog for "Jon Smith"
    When they clear the "Full name" field and save
    Then the message "Enter a full name of 1 to 255 characters." is shown
    And no request is sent

  Scenario: A name longer than 255 characters is rejected before submit
    Given the admin opens the edit dialog for "Jon Smith"
    When they enter a 256-character name and save
    Then the message "Enter a full name of 1 to 255 characters." is shown
    And no request is sent

  Scenario: The backend rejects the name
    Given the admin opens the edit dialog for "Jon Smith"
    When they save a new name and the API answers 422 with a validation list
    Then the message "Enter a full name of 1 to 255 characters." is shown

  Scenario: An unchanged name is not sent
    Given the admin opens the edit dialog for "Jon Smith"
    When they only change the role and save
    Then the PATCH body has no full_name

  Scenario: The email is not editable
    Given the admin opens the edit dialog for "fixed@example.com"
    Then there is no email field in the dialog
    And the email is shown as text

  Scenario: The field keeps a visible keyboard focus style
    Given the admin opens the edit dialog
    Then the "Full name" field has a focus-visible style
