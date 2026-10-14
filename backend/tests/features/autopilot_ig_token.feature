Feature: Instagram token lifecycle
  As the autopilot worker
  I want the Instagram long-lived token stored encrypted and refreshed before it expires
  So that a 60-day token cannot die silently

  Scenario: Token refreshed before expiry
    Given the stored token was refreshed 51 days ago
    When the daily credential step runs
    Then the token is refreshed and expires_at moves forward

  Scenario: Refresh keeps failing near expiry
    Given refresh fails and the token expires in 5 days
    When the daily credential step runs
    Then the owner receives a Telegram alert

  Scenario: Expiry alert is once per day
    Given refresh fails and the token expires in 5 days
    When the daily credential step runs twice on the same day
    Then the owner receives one Telegram alert

  Scenario: Refresh runs once per day
    Given the stored token was refreshed 51 days ago
    When the daily credential step runs twice on the same day
    Then the refresh endpoint is called once

  Scenario: Failed refresh is retried the next day
    Given refresh failed today and the token expires in 5 days
    When the daily credential step runs on the next day
    Then the refresh endpoint is called again

  Scenario: Invalid token alerts even when expiry is far
    Given refresh fails with Meta error 190 and the token expires in 30 days
    When the daily credential step runs
    Then the owner receives a Telegram alert with the regeneration link

  Scenario: Stored token is not plaintext
    Given an Instagram token is saved
    When the credential row is read from the database
    Then the stored value is not the plaintext token
    And the provider still returns the plaintext token

  Scenario: No token is configured
    Given no Instagram credential is stored
    When the token provider is read
    Then the token is empty
    And the publish job fails with instagram_token_missing

  Scenario: Env token seeds the store once
    Given no credential row exists and META_IG_ACCESS_TOKEN is set
    When the application starts
    Then a credential row is inserted with expires_at 60 days ahead
    And a second start does not replace the row

  Scenario: Encryption key missing disables publishing
    Given CREDENTIALS_ENCRYPTION_KEY is unset
    When the application starts
    Then a startup warning is logged
    And autopilot Instagram publishing is disabled

  Scenario: Token is never logged
    Given a stored Instagram token
    When the daily credential step refreshes it
    Then logs do not contain the plaintext token

  # QA r1 H6: manual publishing must not hard-depend on the Fernet key.
  Scenario: Encryption key missing falls back to the env token
    Given CREDENTIALS_ENCRYPTION_KEY is unset or not a Fernet key
    And META_IG_ACCESS_TOKEN is set
    When the manual Instagram publish route asks for a token
    Then it receives the env token
    And a warning is logged without the token
    And startup reports publishing as "env_token_fallback"

  Scenario: Stored token unreadable falls back to the env token
    Given a usable encryption key
    And the credential row is missing or the database cannot be read
    When the manual Instagram publish route asks for a token
    Then it receives the env token
    And a warning names the reason without the token
