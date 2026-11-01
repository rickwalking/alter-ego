Feature: The app always keeps one active admin

  An admin can never leave the app without an active admin. Deactivating or
  demoting the last ACTIVE admin is refused with HTTP 409 and the stable
  "last_admin" code, and nothing is changed. Admins that are already inactive
  do not count: they cannot sign in to the admin area.

  Background:
    Given the database is Postgres

  Scenario: Deactivating the last active admin is refused
    Given I am authenticated as the only active admin
    When I deactivate my own account
    Then the response status should be 409
    And the response code should be "last_admin"
    And the response detail should be "Cannot deactivate the last active admin"
    And my account should still be active

  Scenario: Deactivating is refused when the other admins are inactive
    Given I am authenticated as the only active admin
    And another admin exists who is inactive
    When I deactivate my own account
    Then the response status should be 409
    And the response code should be "last_admin"
    And my account should still be active

  Scenario: Demoting is refused when the other admins are inactive
    Given I am authenticated as the only active admin
    And another admin exists who is inactive
    When I change my own role to editor
    Then the response status should be 409
    And the response code should be "last_admin"
    And my role should still be admin

  Scenario: Demoting and deactivating in one request is refused as a demotion
    Given I am authenticated as the only active admin
    When I change my own role to editor and deactivate my account in one request
    Then the response status should be 409
    And the response code should be "last_admin"
    And my account should still be an active admin

  Scenario: With two active admins one can be deactivated
    Given I am authenticated as an admin
    And another admin exists who is active
    When I deactivate my own account
    Then the response status should be 200
    And my account should be inactive

  Scenario: With two active admins one can be demoted
    Given I am authenticated as an admin
    And another admin exists who is active
    When I change my own role to editor
    Then the response status should be 200
    And my role should be editor

  Scenario: An inactive admin can be demoted while one active admin remains
    Given I am authenticated as the only active admin
    And another admin exists who is inactive
    When I change the inactive admin's role to editor
    Then the response status should be 200

  Scenario: Editors and other changes are not affected by the guard
    Given I am authenticated as the only active admin
    And an active editor exists
    When I deactivate the editor
    Then the response status should be 200

  Scenario: Two admins deactivating each other at once leave one active admin
    Given two active admins
    When each one deactivates the other at the same time
    Then exactly one of the two updates succeeds
    And the other is refused as the last active admin
    And exactly one active admin remains

  Scenario: The active-admin count locks the rows it counts
    Given one transaction has counted the active admins
    When a second transaction counts the active admins
    Then the second count waits until the first transaction ends
    And it then counts the admins that are still active
