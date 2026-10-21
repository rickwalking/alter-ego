# language: en
@AE-0446 @frontend
Feature: Failed admin and login requests show a readable error
  The login page and the admin user dialogs show the API's error message when
  it is a sentence, and their own translated message otherwise.

  Scenario: A handled API error shows its message
    Given the API answers with a string "detail"
    When the request fails
    Then that message is shown

  Scenario: A validation error falls back to the translated message
    Given the API answers a 422 with a list of validation errors
    When the request fails
    Then the translated fallback message is shown, never "[object Object]"

  Scenario: A non-JSON error falls back to the translated message
    Given a proxy answers with a plain-text error page
    When the request fails
    Then the translated fallback message is shown
