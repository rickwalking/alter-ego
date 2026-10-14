Feature: Research scraper SSRF guard (QA r1 S-W1)
  Autopilot feeds third-party story URLs into the Playwright research scraper.
  A URL is scraped only when every address its host resolves to is public,
  and every request the page makes is re-checked.

  Scenario: Public host is allowed
    Given a URL whose host resolves only to a public address
    When the SSRF guard checks the URL
    Then the URL is allowed

  Scenario Outline: Host resolving to an internal address is refused
    Given a URL whose host resolves to "<address>"
    When the SSRF guard checks the URL
    Then the URL is refused

    Examples:
      | address         |
      | 10.0.0.5        |
      | 192.168.1.10    |
      | 127.0.0.1       |
      | 169.254.169.254 |
      | 100.64.0.1      |
      | fd00::1         |
      | ::1             |
      | fe80::1%eth0    |
      | 0.0.0.0         |

  Scenario: One internal answer among public ones is refused
    Given a URL whose host resolves to a public and a private address
    When the SSRF guard checks the URL
    Then the URL is refused

  Scenario: DNS failure fails closed
    Given a URL whose host cannot be resolved
    When the SSRF guard checks the URL
    Then the URL is refused

  Scenario Outline: Docker service names and single-label hosts are refused without DNS
    Given the URL "<url>"
    When the SSRF guard checks the URL
    Then the URL is refused
    And no DNS lookup is made

    Examples:
      | url                         |
      | http://redis:6379/          |
      | http://postgres/            |
      | http://minio:9000/bucket    |
      | http://langfuse:3000/       |
      | http://intranet/            |
      | http://metadata.google.internal/ |
      | ftp://example.com/file      |

  Scenario: Redirect hop to an internal address is aborted
    Given a page whose navigation redirects to "http://169.254.169.254/latest"
    When the scraper's route guard sees each request
    Then the public request is continued
    And the redirect hop is aborted
    And the scrape is refused after navigation

  Scenario: Redirect hop the browser did not route is still refused
    Given the page recorded a request to a host resolving to a private address
    When the scraper verifies the navigation
    Then the scrape is refused

  Scenario: Unsafe first URL never launches the browser
    Given a URL whose host resolves to a private address
    When the research tool scrapes it
    Then it raises an unsafe-target error before Playwright starts
