Feature: Frontend Authentication and Route Guards

  Scenario: Unauthenticated user is redirected from dashboard
    Given I am not logged in
    When I navigate to "/dashboard/chat"
    Then I should be redirected to "/login"

  Scenario: Unauthenticated user can read public blog
    Given I am not logged in
    When I navigate to "/blog/my-public-post"
    Then I should see the blog content
    And the URL should remain "/blog/my-public-post"

  Scenario: Editor cannot access admin panel
    Given I am logged in as an editor
    When I navigate to "/admin/users"
    Then I should be redirected to "/403"

  Scenario: Admin sees user management
    Given I am logged in as an admin
    When I navigate to "/admin/users"
    Then I should see a table of users
    And I should see a "Create User" button

  Scenario: Admin creates user through UI
    Given I am logged in as an admin
    And I am on "/admin/users"
    When I click "Create User"
    And I fill in "Email" with "new@test.com"
    And I fill in "Full Name" with "New User"
    And I select "Editor" from the role dropdown
    And I click "Create"
    Then I should see a success message containing a temporary password
    And the user table should contain "new@test.com"

  Scenario: Authenticated user sees navigation based on role
    Given I am logged in as an admin
    When I open the navigation menu
    Then I should see "Chat", "Knowledge Base", "Blog", "Create", and "Admin"

  Scenario: Editor sees limited navigation
    Given I am logged in as an editor
    When I open the navigation menu
    Then I should see "Chat", "Knowledge Base", "Blog", and "Create"
    And I should not see "Admin"

  Scenario: Visitor sees public navigation only
    Given I am not logged in
    When I open the navigation menu
    Then I should see "Blog"
    And I should see "Login"
    And I should not see "Chat", "Knowledge Base", or "Create"
