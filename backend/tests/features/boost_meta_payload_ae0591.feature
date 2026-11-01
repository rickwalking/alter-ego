Feature: Boost launch sends the capped audience and run window, and keeps Meta's error details
  The ad set carries the stored audience (Brazil only, ages 18-65) and a start and end
  time so Meta itself stops at the shipped caps. Every Marketing API failure keeps
  which call failed and Meta's own error fields, never the token, on the failure event
  and in the log. A validate-only check posts the real bodies without creating anything.

  Scenario: The ad set carries the capped Brazil audience and the run window
    Given an approved boost for Brazil, ages 18 to 65, running 3 days
    When the boost is launched
    Then the ad set targets Brazil, ages 18 to 65, on the Instagram feed with advantage audience off
    And the ad set runs from now until 3 days later

  Scenario: A requested future start is kept and the end is the start plus the days
    Given an approved boost asked to start tomorrow for 2 days
    When the boost is launched
    Then the ad set starts tomorrow and ends 2 days after that
    And the launched request stores that start and end

  Scenario: The creative and the ad use the existing Instagram post form
    Given an approved boost
    When the boost is launched
    Then the creative names the Page, the Instagram user and the source Instagram media
    And the ad joins the ad set and the creative paused

  Scenario: An audience outside Brazil is refused before any Meta call
    Given an approved boost whose stored audience includes a country other than Brazil
    When the boost is launched
    Then the launch fails with the permanent error country_not_allowed
    And no Marketing API request is made

  Scenario: An age band outside 18 to 65 is refused before any Meta call
    Given an approved boost whose stored audience starts at age 16
    When the boost is launched
    Then the launch fails with the permanent error audience_invalid
    And no Marketing API request is made

  Scenario: A run longer than the 7-day cap is refused before any Meta call
    Given an approved boost stored with 8 days
    When the boost is launched
    Then the launch fails with the permanent error days_over_cap
    And no Marketing API request is made

  Scenario: A run of zero days is refused before any Meta call
    Given an approved boost stored with 0 days
    When the boost is launched
    Then the launch fails with the permanent error boost_schedule_invalid

  Scenario: A creative refused for an app in development mode fails with meta_app_dev_mode
    Given Meta answers the creative with code 100 and subcode 1885183
    When the boost is launched
    Then the launch fails with the permanent error meta_app_dev_mode
    And the error details name the creative call with Meta's title, message and trace id

  Scenario: A media preflight the ads token cannot read fails with meta_media_unreadable
    Given Meta answers the media preflight with code 100 and subcode 33
    When the boost is launched
    Then the launch fails with the permanent error meta_media_unreadable
    And the error details name the preflight_media call

  Scenario: Every failing call is named with Meta's error fields
    Given Meta answers one launch call with an error
    When the boost is launched
    Then the error details name that call with Meta's code, subcode and type
    And the error code is meta_ followed by Meta's code

  Scenario: Meta's error details never carry the token or the appsecret proof
    Given Meta echoes the token and the appsecret proof in its error message
    When the boost is launched
    Then the error details show them redacted

  Scenario: A server error stays transient and keeps Meta's details
    Given Meta answers the campaign with a 500 and an error body
    When the boost is launched
    Then the launch fails with the transient error meta_transient
    And the error details keep Meta's code and the HTTP status

  Scenario: A body that is not an error object keeps a stable code
    Given Meta answers with a non-JSON body or a JSON list
    When a Graph call reads the body
    Then a non-JSON body is meta_transient and a JSON list is meta_bad_body

  Scenario: The worker stores Meta's error details on the failure event and logs them
    Given an approved boost and Meta refusing the creative for an app in development mode
    When the worker ticks with spending enabled
    Then the request is stored as failed with error code meta_app_dev_mode
    And the failure carries Meta's error details for the event
    And one structured log line holds the details without the token

  Scenario: The failure event on Postgres stores Meta's error details
    Given a boost request that failed on the creative call
    When the failure is saved on Postgres
    Then the failure event detail holds the error code and Meta's error fields

  Scenario: The validate-only check sends only validate_only POSTs
    Given a stored boost request and Meta accepting every call
    When the validate-only check runs without parent ids
    Then the campaign and the creative are posted with execution_options validate_only
    And the ad set and the ad are reported with their body and no token

  Scenario: With parent ids the ad set and the ad are validated too
    Given a stored boost request and existing campaign, ad set and creative ids
    When the validate-only check runs
    Then every POST carries execution_options validate_only

  Scenario: A POST without validate_only is refused before it is sent
    Given the validate-only graph
    When a body without execution_options validate_only is posted
    Then it is refused and no request is sent

  Scenario: The validate-only check reports Meta's error fields per call
    Given Meta refusing the creative for an app in development mode
    When the validate-only check runs
    Then the creative outcome is failed with meta_app_dev_mode and Meta's details
    And the printed lines never hold the token

  Scenario: The validate-only check reports an audience outside the caps
    Given a stored boost request whose audience includes a country other than Brazil
    When the validate-only check runs
    Then the ad set outcome is failed with country_not_allowed

  Scenario: The validate-only command loads the request and prints one line per call
    Given a stored boost request and an ads token
    When the validate-only command runs for the request id
    Then it prints one JSON line per call and exits 0 when every sent call passed

  Scenario: The validate-only command refuses a missing request, a missing token or a bad id
    Given the validate-only command
    When the request is missing, the token is empty or the id is not a UUID
    Then it exits non-zero without calling Meta
