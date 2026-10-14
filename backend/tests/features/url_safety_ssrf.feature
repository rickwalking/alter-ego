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

  # QA r2 R2: Playwright does not route redirect hops, so the browser never
  # navigates. The document is fetched hop by hop with redirects off.
  Scenario: A redirect to an internal address is never requested
    Given a public page that answers 302 with Location "http://127.0.0.1/internal"
    When the research fetcher follows the redirect chain
    Then the hop to 127.0.0.1 is refused before it is requested
    And the internal server never receives a request
    And at most five redirects are followed

  Scenario: The rendered page cannot reach the network
    Given the fetched HTML references an image on "http://169.254.169.254/x"
    When the scraper renders it with page.set_content
    Then JavaScript is off and every page request is aborted
    And the page is never navigated

  Scenario: Unsafe first URL never launches the browser
    Given a URL whose host resolves to a private address
    When the research tool scrapes it
    Then it raises an unsafe-target error before Playwright starts

  # QA r3 Q5: parity with the old Chromium navigation.
  Scenario: A research fetch ends at one overall deadline
    Given a redirect chain whose hops are each slow
    When the research fetcher follows it
    Then the whole fetch, all hops included, ends at 15 seconds
    And the source is skipped like a failed scrape

  Scenario: Only text documents are rendered
    Given a URL that serves "application/pdf", an image, binary data, or no content type
    When the research tool scrapes it
    Then the source is skipped and Chromium never starts
    And "text/html" and "application/xhtml+xml" are rendered
    And "text/plain" is returned as text without Chromium

  Scenario: The fetch sends browser headers and honours the page charset
    Given a page encoded in ISO-8859-1
    When the research fetcher requests it with a browser User-Agent, Accept and Accept-Language
    Then the text is decoded with the header charset, else the meta charset, else UTF-8 with replacement
    And a page that needs JavaScript comes back as its static HTML

  # QA r3 Q6: no DNS prefetch or preconnect from rendered HTML.
  Scenario: Resource hints in the page never reach the network
    Given fetched HTML with dns-prefetch, preconnect, prefetch, preload and prerender links
    When the scraper renders it
    Then those links are removed before page.set_content
    And Chromium is launched with "--dns-prefetch-disable"
