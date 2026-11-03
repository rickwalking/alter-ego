Feature: A stale user write never restores an old password hash or token version
  A user write saves only the fields the operation changed, from the user row
  read locked inside the Unit of Work. A profile or role edit never writes the
  password hash or the token version, so a password change or an admin reset
  that commits while the edit is in flight survives it: the revoked password
  stays revoked and the logged-out sessions stay logged out.

  Scenario: A fresh user has no changed fields
    Given a user built or loaded from storage
    Then it reports no changed fields

  Scenario: Every assigned persisted field is reported changed
    Given a user built from storage
    When it is renamed, deactivated, given a role, a new email or a new password
    Then exactly the fields those operations assign are reported changed
    And a field assigned directly is reported changed too
    And the id and the creation time are never reported

  Scenario: A stale profile edit keeps the new password and token version
    Given a user read before a password change commits
    When that stale copy is renamed and saved after the change
    Then the stored name is the new one
    And the stored hash and token version are the ones of the password change

  Scenario: A save with no changed field writes no column
    Given a user read from storage with nothing changed
    When it is saved
    Then no stored column changes

  Scenario: An admin edit reads the user locked inside the unit of work
    Given a user
    When an admin renames them, changes their role or deactivates them
    Then the user is read locked and the change is committed once
    And an edit of the role or active state locks the active admins before the user

  Scenario: A refused admin edit commits nothing
    Given the only active admin
    When an admin tries to deactivate them
    Then the edit is refused and nothing is committed

  Scenario: A user service edit reads the user locked inside the unit of work
    Given a user
    When the user service updates their profile or assigns them a role
    Then the user is read locked and the change is committed once

  Scenario: A password change reads the user locked inside the unit of work
    Given a user changing their password
    When the current password is wrong
    Then the user was read locked, nothing is committed and the unit of work rolls back

  Scenario: An admin profile edit waits for a password change that holds the user row
    Given a password change that holds the user row lock on Postgres
    When an admin renames the user meanwhile
    Then the rename waits on the lock
    And once the change commits, the new hash, the bumped token version and the new name are all stored

  Scenario: Admin edits queued behind a password change never deadlock
    Given two active admins on Postgres and a password change holding the first admin's row
    When one admin edit deactivates the second admin and another deactivates the first, meanwhile
    Then both edits wait, and once the change commits neither deadlocks
    And one edit is allowed, the other refused, and one active admin is left
