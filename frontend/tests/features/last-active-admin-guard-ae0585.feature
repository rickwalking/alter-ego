Feature: The users area keeps one active admin

  The edit-user dialog never lets the admin demote or deactivate the last
  active admin, and explains why. If the API still refuses the change with
  the "last_admin" code, the dialog shows a Portuguese or English message,
  never the English API text.

  Scenario: The role and active controls are locked for the last active admin
    Given the list has exactly one active admin
    When the admin opens the edit dialog of that admin
    Then the role select and the active checkbox are disabled
    And both are described by a message explaining that the last active admin cannot be demoted or deactivated

  Scenario: The controls stay enabled when another admin is active
    Given the list has two active admins
    When the admin opens the edit dialog of one of them
    Then the role select and the active checkbox are enabled
    And no last-active-admin explanation is shown

  Scenario: Inactive admins do not count as active admins
    Given the list has one active admin and one inactive admin
    When the admin opens the edit dialog of the active admin
    Then the role select and the active checkbox are disabled

  Scenario: Other users keep their controls
    Given the list has exactly one active admin
    When the admin opens the edit dialog of an editor
    Then the role select and the active checkbox are enabled

  Scenario: A last-admin refusal from the API shows a translated message
    Given the admin saves a change the API refuses with 409 "last_admin"
    Then the dialog shows the translated last-admin message
    And the English API detail is not shown
