Feature: Users area polish

  The /admin users area follows the dashboard: the same dark theme, the same
  sidebar (a drawer on a phone) with the PT/EN switch, real modal dialogs, and
  messages in the reader's language instead of the backend's English text.

  Scenario: Every admin dialog is a real modal
    Given the admin opens the create, edit, reset-password or delete dialog
    Then the dialog has role "dialog" (the delete dialog "alertdialog")
    And it is modal and labelled by its title
    And keyboard focus moves into the dialog

  Scenario: Escape closes a dialog and focus returns to the opener
    Given the admin opened the create-user dialog with the "Create user" button
    When they press Escape
    Then the dialog closes
    And focus is back on the "Create user" button

  Scenario: Tab stays inside an open dialog
    Given an admin dialog is open
    When the admin tabs past the last button
    Then focus wraps to the first control of the dialog

  Scenario: A duplicate email shows a translated message
    Given the admin fills the create-user form with an email already in use
    When they submit it and the API answers 409 with code "user_email_exists"
    Then the dialog says "A user with this email already exists." in the reader's language
    And the English API text is not shown

  Scenario: The password minimum is shown before submitting
    Given the admin opens the create-user dialog
    Then the password field says it needs at least 12 characters

  Scenario: A short password is refused without a request
    Given the admin types a password of 5 characters
    When they submit the create-user form
    Then the password field is marked invalid with the 12-character message
    And no request is sent

  Scenario: A 422 field error is shown on its field
    Given the API answers 422 with an error on "email"
    Then the email field is marked invalid with the translated email message

  Scenario: An unknown create failure keeps the generic message
    Given the API answers 500 with an English detail
    Then the dialog shows "Failed to create user." in the reader's language

  Scenario: A last-admin or self-delete refusal is translated
    Given the API answers 409 with code "last_admin" or "self_delete"
    Then the dialog shows the matching translated message

  Scenario: A deactivated account sees a translated login message
    Given a deactivated user signs in with the right password
    When the API answers 401 with code "user_inactive"
    Then the login page says the account is deactivated in the reader's language
    And the English API text is not shown

  Scenario: Wrong credentials keep the translated invalid-credentials message
    Given the API answers 401 with no code
    Then the login page shows the translated invalid-credentials message

  Scenario: The admin sidebar is a drawer on a phone
    Given the admin is on "/admin/users" at 390 px wide
    Then the sidebar is off screen and a menu button is shown
    When they press the menu button
    Then the sidebar opens with focus inside it
    When they press Escape or tap the overlay
    Then the sidebar closes

  Scenario: The admin shell has the PT/EN switch
    Given the admin is on "/admin/users"
    Then the sidebar shows the EN | PT language switch

  Scenario: User rows stack as cards on a phone
    Given the admin is on "/admin/users" at 390 px wide
    Then each user is a card with name, email, role, status and creation date
    And the page has no horizontal scroll

  Scenario: Row actions are large enough to tap
    Given the admin is on "/admin/users" at 390 px wide
    Then the edit, reset-password and delete buttons are at least 44 px tall
    And the dialog buttons are at least 44 px tall

  Scenario: The role badge is readable
    Given a user with the role "editor" or "admin"
    Then the badge shows the translated role name
    And its text has a contrast of at least 4.5:1 against the card
