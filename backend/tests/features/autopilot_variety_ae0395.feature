Feature: Autopilot carousels vary their palette (AE-0395)
  The "auto" palette put nearly every AI topic on the same blue/amber theme.
  The autopilot now rotates a dark built-in theme per São Paulo day.

  Scenario: Consecutive days get different palettes
    Given two consecutive São Paulo days
    When the autopilot picks the palette for each day
    Then the two palettes differ and both are dark built-in themes

  Scenario: The day follows São Paulo, not UTC
    Given 23:30 in São Paulo, already the next day in UTC
    When the autopilot picks the palette
    Then it is the palette of the São Paulo day

  Scenario: The overused blue/amber theme is not in the rotation
    When the rotation is listed
    Then ai_competition is not in it

  Scenario: The autopilot creates its carousel with the day's palette
    Given a queued run on a São Paulo day
    When the driver creates the carousel
    Then the project's theme is that day's palette
