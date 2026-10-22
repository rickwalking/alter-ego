Feature: Login return path stays on this site
  As the site owner
  I want the post-login return path to be a same-origin page only
  So that a crafted login link can never send a signed-in user to another site

  Scenario: A same-origin return path is kept
    Given the login link carries "redirect=/dashboard/calendar?view=month#today"
    When I sign in
    Then I land on "/dashboard/calendar?view=month#today"

  Scenario: A missing or empty return path falls back to the dashboard chat
    Given the login link carries no usable "redirect" value
    When I sign in
    Then I land on "/dashboard/chat"

  Scenario: Absolute and scheme-relative URLs are rejected
    Given the login link carries "redirect=https://example.org/" or "redirect=//example.org"
    When I sign in
    Then I land on "/dashboard/chat"

  Scenario: Backslash tricks are rejected
    Given the login link carries "redirect=/\example.org" or "redirect=/%5Cexample.org"
    When I sign in
    Then I land on "/dashboard/chat"

  Scenario: Control characters and encoded separators are rejected
    Given the login link carries a tab, a newline or an encoded slash that turns the path into "//host"
    When I sign in
    Then I land on "/dashboard/chat"

  Scenario: A return path back to the login page is rejected
    Given the login link carries "redirect=/login?redirect=/dashboard"
    When I sign in
    Then I land on "/dashboard/chat"

  Scenario: The session-expired logout keeps only a safe return path
    Given an API call answered 401 and the client opens "/auth/logout?redirect=/\example.org"
    When the logout handler redirects to the login page
    Then the login URL carries "redirect=/dashboard/chat"
