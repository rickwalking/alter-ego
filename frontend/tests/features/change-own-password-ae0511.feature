Feature: Change my own password, and change a temporary one before using the app
  Any signed-in user can change their password from the dashboard. After an
  admin resets it, the user is sent to the change-password screen and cannot
  use the rest of the app until they change it.

  Scenario: The change-password page has its own title
    Given the change-password page
    Then its title is "Change password · Pedro Marins" in English and "Alterar senha · Pedro Marins" in Portuguese

  Scenario: A user changes their password from the dashboard
    Given a signed-in user on the change-password page
    When they enter the current password and a matching new password
    Then the change is sent to the API
    And a success message is shown and the form is cleared

  Scenario: A wrong current password shows a clear error
    Given a signed-in user on the change-password page
    When the API answers 401 with the code current_password_incorrect
    Then the form says the current password is wrong
    And the user stays signed in

  Scenario: The form checks the new password before sending it
    Given a signed-in user on the change-password page
    When the new password is too short, the confirmation differs, or it equals the current one
    Then a translated message explains the problem and nothing is sent

  Scenario: API refusals are translated
    Given a signed-in user on the change-password page
    When the API answers password_unchanged, 422, 429, another error, or the network fails
    Then the form shows a translated message for each

  Scenario: A user with a temporary password is sent to the change-password page
    Given the session reports must_change_password
    When the user opens any other dashboard or admin page
    Then they are sent to the change-password page and the page content is not shown

  Scenario: The change-password page explains a forced change
    Given the session reports must_change_password
    When the change-password page opens
    Then it explains that the temporary password must be changed before continuing

  Scenario: Changing the temporary password lets the user continue
    Given the session reports must_change_password
    When the user changes the password
    Then the session is refreshed and the user is sent to the dashboard

  Scenario: An API call refused with password_change_required goes to the change page
    Given a dashboard request answered 403 with the code password_change_required
    Then the browser goes to the change-password page instead of the access denied page

  Scenario: The sidebar links to the change-password page
    Given a signed-in user
    Then the sidebar footer has a change-password link

  Scenario: The reset dialog shows the temporary password once with a must-change note
    Given an admin who reset another user's password
    Then the temporary password is shown once with a copy button
    And a note says the user must change it at the next sign-in
