Feature: production CSP carries no development artifacts (AE-0305)
  The Content-Security-Policy is defined in exactly ONE layer (next.config.ts
  via the csp constants builder); nginx stays verifiably silent. The
  http://localhost:8000 img-src entry is a dev-only convenience and must never
  ship in the production policy.

  Scenario: production policy excludes the dev backend image source
    Given the CSP is built for the production environment
    Then img-src does not contain http://localhost:8000
    And every other directive is unchanged from the development policy

  Scenario: development keeps local backend images working
    Given the CSP is built for a non-production environment
    Then img-src contains http://localhost:8000

  Scenario: the CSP has a single authoritative layer
    Given the nginx configs and next.config.ts
    Then no nginx config sets a Content-Security-Policy header
    And next.config.ts contains no inline CSP literal (it must use the builder)

  Scenario: core protections never regress silently
    Given the CSP is built for any environment
    Then frame-ancestors is 'none' and base-uri and form-action are 'self'
