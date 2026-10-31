Feature: Search and filter users on the admin users page

  An admin on /admin/users sees every user (the backend caps the list at
  1000). The "Buscar"/"Search" field and the role/status filters narrow the
  rows client-side, so an admin with many users can find one quickly. Search
  matches name or email and ignores case and accents, because names are
  written with accents while keyboards often are not.

  Scenario: Search matches a name regardless of case and accents
    Given the admin is on "/admin/users" and the list has a user named "João Silva"
    When they type "joao" in "Buscar"
    Then the row for "João Silva" is shown
    And rows without "joao" in name or email are hidden

  Scenario: Search matches an email
    Given the admin is on "/admin/users"
    When they type "ana@example.com" in "Buscar"
    Then only the row for "ana@example.com" is shown

  Scenario: Role filter narrows the rows
    Given the admin is on "/admin/users" with users of different roles
    When they pick "Admin" in the role filter
    Then only rows with the "admin" role are shown
    When they pick "All roles"
    Then every row is shown again

  Scenario: Status filter narrows the rows
    Given the admin is on "/admin/users" with active and inactive users
    When they pick "Inactive" in the status filter
    Then only rows with status "Inactive" are shown

  Scenario: Combined filters must all match
    Given the admin is on "/admin/users"
    When they type a search term and pick a role and a status
    Then only rows matching all three are shown

  Scenario: No match shows a filter-specific empty message
    Given the admin is on "/admin/users"
    When they type a term that matches no name or email
    Then the table is replaced by a "no users match the filters" message

  Scenario: Clearing the filters restores the full list
    Given the admin filtered the list down to one row
    When they clear "Buscar" and set the role and status filters back to "all"
    Then the full list is shown again

  Scenario: An empty user list keeps the no-users message
    Given the admin is on "/admin/users" and there are no users
    Then the "no users found" message is shown
    And the "no users match the filters" message is not shown

  Scenario: Search and filter controls are keyboard accessible
    Given the admin is on "/admin/users"
    When they press Tab from the search field
    Then focus moves to the role filter and then to the status filter
    And each control is announced by its label
