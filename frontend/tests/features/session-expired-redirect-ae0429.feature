Feature: An expired session logs out through a front-end route (AE-0429)
  As a signed-in user whose token expired
  I want the app to clear my session and send me to the login page
  So that I never land on a backend JSON error page

  # nginx proxies every /api/* request to FastAPI, so the logout handler must
  # live outside /api (see docs/decisions or docs/architecture for the proxy).
  # Tests:
  #   src/app/auth/logout/route.test.ts
  #   src/lib/api-client.test.ts
  #   src/constants/middleware.test.ts

  Background:
    Given nginx sends every "/api/*" request to the FastAPI backend

  Scenario: A 401 redirects to the front-end logout route
    Given the API answers 401 on a dashboard request
    When the API client handles the response
    Then the browser navigates to "/auth/logout?redirect=<path+query>"
    And the redirect target is not under "/api/"
    And the redirect carries the current path and query

  Scenario: The logout handler clears the session and returns to login
    Given a request to "/auth/logout?redirect=/dashboard/create/abc?step=content"
    When the logout handler runs
    Then the access_token cookie is cleared
    And the backend logout POST is attempted best-effort
    And the browser is redirected to "/login?redirect=/dashboard/create/abc?step=content&error=session_expired"

  Scenario: An external redirect is dropped
    Given a request to "/auth/logout?redirect=//evil.com"
    When the logout handler runs
    Then the access_token cookie is cleared
    And the browser is redirected to "/login?redirect=/dashboard/chat&error=session_expired"

  Scenario: An absolute external redirect is dropped
    Given a request to "/auth/logout?redirect=https://evil.com"
    When the logout handler runs
    Then the browser is redirected to "/login?redirect=/dashboard/chat&error=session_expired"

  Scenario: A request without a redirect param still reaches login
    Given a request to "/auth/logout"
    When the logout handler runs
    Then the browser is redirected to "/login?error=session_expired"

  Scenario: A failing backend logout still ends the front-end session
    Given the backend logout POST fails
    When the logout handler runs
    Then the access_token cookie is cleared
    And the browser is redirected to "/login?error=session_expired"

  # AE-0431: under the Next standalone server, request.url carries the bind
  # address (0.0.0.0:3000); the Location must use the proxied Host instead.
  Scenario: The login Location never exposes the internal server host
    Given a request to "/auth/logout?redirect=/dashboard/create/abc?step=content"
      whose URL host is the standalone server bind address "0.0.0.0:3000"
      with headers "Host: marinssolutions.com" and "X-Forwarded-Proto: https"
    When the logout handler runs
    Then the access_token cookie is cleared
    And the browser is redirected to "https://marinssolutions.com/login?redirect=/dashboard/create/abc?step=content&error=session_expired"
    And the Location header does not contain "0.0.0.0" or "localhost"

  Scenario: The logout route is reachable without a token
    Given an unauthenticated request to "/auth/logout"
    When the middleware classifies the path
    Then the route is public and is not redirected to login

  Scenario: The redirect target guard cannot regress
    Then the session-expired redirect target is not under "/api/"
    And no caller builds a session-expired redirect under "/api/"
