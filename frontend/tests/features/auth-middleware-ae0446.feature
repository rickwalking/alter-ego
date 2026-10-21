# language: en
@AE-0446 @frontend @auth
Feature: The route guard sends each visitor to the right page
  Pins the Next.js middleware behavior (it had no tests) before it was split
  into small functions.

  Scenario: Public pages and static assets need no session
    When an anonymous visitor opens the home page or a static asset
    Then the request passes through

  Scenario: An anonymous visitor is sent to login with a return path
    When an anonymous visitor opens a dashboard page
    Then they are redirected to /login with the page as the return path

  Scenario: An expired session is cleared
    Given the session cookie no longer verifies
    When the visitor opens a page
    Then the cookie is cleared
    And a dashboard page redirects to login while the login page renders

  Scenario: A signed-in user skips the login page
    Given a valid session
    When the user opens /login
    Then they are redirected to the dashboard chat

  Scenario: Roles gate admin and editor pages
    Given a valid session
    Then admin pages need the admin role
    And editor dashboard pages need the editor or admin role
    And the dashboard chat is open to every signed-in user
