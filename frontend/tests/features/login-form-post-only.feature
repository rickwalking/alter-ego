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

  Scenario: The no-JavaScript sign-in sets the same session cookie as the normal login
    When a no-JavaScript sign-in succeeds
    Then the session cookie is HttpOnly and SameSite=Strict
    And it lives as long as the backend's token (ACCESS_TOKEN_EXPIRE_MINUTES, 60 by default)

  Scenario: A rate-limited sign-in without JavaScript says to wait
    Given the backend answers 429 to a sign-in
    When the form is posted to "/auth/login", or the hydrated form signs in
    Then the login page says there were too many attempts, not that the credentials are wrong

  Scenario: The no-JavaScript sign-in is rate-limited per client
    Then nginx limits "/auth/login" per client IP in both server configs
