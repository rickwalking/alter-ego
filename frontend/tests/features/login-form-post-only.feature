@AE-0481 @frontend @security
Feature: Credentials never go into a URL
  As anyone signing in
  I want the login form to send my email and password only in a POST body
  So that a submit before the page hydrates, or without JavaScript, never leaves my password in the address bar,
  the browser history or server logs

  Scenario: The login form is a POST form before hydration
    When the login page is rendered on the server
    Then its form posts to "/auth/login"

  Scenario: A login form submitted without JavaScript signs in by POST
    Given valid credentials
    When this site's login page posts the form to "/auth/login"
    Then the session cookie is set and I land on the dashboard

  Scenario: A failed sign-in without JavaScript returns an error code only
    Given the backend rejects the credentials, is unreachable, or a field is missing
    When the form is posted to "/auth/login"
    Then I am sent back to the login page with "error=invalid_credentials"
    And the URL carries neither the email nor the password

  Scenario: A sign-in posted from another site is refused
    When another site (or a request without same-origin proof) posts a login form to "/auth/login"
    Then the answer is 403 and the backend is not called

  Scenario: Every form with a password field posts
    Then no form with a password field in the source uses the default GET method

  Scenario: A login form submitted without JavaScript never puts credentials in the URL
    Given JavaScript is disabled
    When I fill in the login form and click "Sign in"
    Then the browser posts to "/auth/login"
    And no visited URL contains the email or the password
