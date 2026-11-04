Feature: The content gate event names the rules that fired (AE-0613)

  A content_gate generation event stores which presentation rules fired, as rule
  ids from the known violation constants. It never stores a message, slide text,
  field value or anything user-written. The sanitizer keeps one string at 64
  characters, so blockers are kept first and every omission is marked.

  Scenario: A blocked gate stores the codes of the rules that fired
    Given a content gate report with two blockers and a repeated code
    When the content phase artifacts are recorded
    Then the content_gate event stores the distinct codes sorted and joined by "."
    And violation_count and blocking_count are unchanged

  Scenario: A passing gate stores no codes
    Given an empty content gate report
    When the content phase artifacts are recorded
    Then the content_gate event has no violation_codes key
    And the event is not marked truncated

  Scenario: A violation with a message and slide text stores the code only
    Given a blocking violation whose message and fields carry slide text
    When the event is stored and read through the generation log API
    Then the stored row and the API response name the code
    And neither contains the message, the slide text or the field value

  Scenario: An unknown or free-text code is dropped
    Given a report with a known code, an unknown code and free text in the code field
    When the content phase artifacts are recorded
    Then only the known code is stored
    And the event is marked truncated

  Scenario: A malformed violation entry never breaks the event
    Given a report whose entries are not objects or whose code is not a string
    When the content phase artifacts are recorded
    Then the event has no violation_codes key
    And the event is marked truncated

  Scenario: Many codes stay within the sanitizer bounds
    Given a report that fires every known rule
    When the content_gate details are sanitized
    Then violation_codes survives the sanitizer unchanged within 64 characters
    And the event is marked truncated

  Scenario: Blockers are kept ahead of warnings when space runs out
    Given a report with warnings that sort first and one blocker that sorts last
    When the content phase artifacts are recorded
    Then the blocker's code is stored

  Scenario: The sanitizer still bites around the new key
    Given details with a key that is not allowlisted
    And violation_codes values that are oversized or unsafe
    When the details are sanitized
    Then the key and the values are dropped and the details are marked truncated
