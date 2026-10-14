Feature: Secrets in request URLs never reach the logs
  # QA r1 S-W2: Telegram puts the bot token in the URL path and Instagram
  # takes access_token as a query parameter. httpx logs request URLs at INFO.

  Scenario: httpx request lines are not logged at INFO
    Given logging is configured by setup_logging
    When httpx logs "HTTP Request: POST https://api.telegram.org/bot123:abc/sendMessage" at INFO
    Then nothing is written

  Scenario: A warning with a bot URL and an access token is redacted
    Given logging is configured by setup_logging
    When a stdlib warning contains a Telegram bot URL and an access_token query
    Then the line shows "/bot<redacted>" and "access_token=<redacted>"
    And neither secret appears

  Scenario: A structlog event with a secret URL is redacted
    Given logging is configured by setup_logging
    When a structlog event carries a URL with an access_token query
    Then the rendered line shows "access_token=<redacted>"
