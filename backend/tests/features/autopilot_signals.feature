Feature: Autopilot signal collection
  The scout reads one JSON bundle of free, typed, deduped trend signals.
  Collectors run in the backend. Tests mock every upstream call.

  Scenario: Bundle combines all free sources
    Given every collector returns at least one signal
    When the scout requests the signals bundle
    Then the bundle contains signals from x_search, hn, hf_papers, rss, bluesky and github
    And no URL appears twice

  Scenario: One source failing does not fail the bundle
    Given the Bluesky collector times out
    When the scout requests the signals bundle
    Then the response status is 200
    And errors contains "bluesky"

  Scenario: X search keeps only recent status posts
    Given ddgs returns a profile URL, a 3-day-old status and a 2-hour-old status
    When the X collector runs
    Then only the 2-hour-old status is kept with its snippet text

  Scenario: Mirror resolver falls back on legal block
    Given the resolver is "mirror" and the mirror answers HTTP 451
    When a status URL is resolved
    Then the resolver returns nothing and the snippet is used

  Scenario: Repeated requests reuse the cached bundle
    Given the collectors have already produced a bundle
    When the scout requests the signals bundle again within 30 minutes
    Then the collectors are not called again

  Scenario: The bundle is capped
    Given the collectors return more than 200 signals
    When the scout requests the signals bundle
    Then the bundle contains 200 signals
