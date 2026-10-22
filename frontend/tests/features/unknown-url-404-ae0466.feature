Feature: Unknown URLs answer 404 for everyone
  As a visitor following a broken link to marinssolutions.com
  I want the not-found page instead of a login wall
  So that only pages that really need a session ask me to sign in

  Scenario: A logged-out visitor on an unknown URL gets the not-found page
    Given I am not signed in
    When I open "/nonexistent" or "/blog-archive/2024"
    Then the request is not redirected and the not-found page answers 404

  Scenario: A logged-out visitor on a protected page is still sent to login
    Given I am not signed in
    When I open "/dashboard/calendar", "/admin/users" or the legacy "/knowledge"
    Then I am redirected to "/login" with the return path

  Scenario: A stale session cookie on an unknown URL is not turned into a login redirect
    Given my session cookie no longer verifies
    When I open "/nonexistent"
    Then the request is not redirected
