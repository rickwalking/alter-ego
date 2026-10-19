Feature: The EN column exposes every structured field the PT column has (AE-0430)

  Prod carousel 5344b6c6: PT slide 1 had a TL;DR strip, EN had none, and the
  EN column of the manual editor offered no TL;DR field, so the blocking
  "translation_shape_mismatch" could not be fixed by hand.

  Scenario: The EN column shows a TL;DR field when only PT has one
    Given an editable intro slide whose PT payload has a "tldr_strip" and EN has none
    When the content review renders the EN column
    Then the EN column shows an empty, editable TL;DR field

  Scenario: Typing in the mirrored EN TL;DR creates the field on the EN payload
    Given the EN column shows the mirrored TL;DR field
    When the reviewer types "Grok Bot books by phone" into it
    Then the edited EN payload carries "tldr_strip" = "Grok Bot books by phone"

  Scenario: The EN column shows the PT items when EN has no item list
    Given an editable closing slide whose PT payload has 3 actions and EN has none
    When the content review renders the EN column
    Then the EN column shows 3 editable action items with empty title and body

  Scenario: Editing a mirrored EN item creates the EN list from the PT shape
    Given the EN column shows the mirrored action items
    When the reviewer types an EN body for action 2
    Then the edited EN payload has 3 actions with the PT icons
    And only action 2 carries the typed body

  Scenario: An untouched slide is not sent as changed
    Given the EN column shows mirrored fields the reviewer did not edit
    When the reviewer submits the manual fixes
    Then that slide is not in the changed slides
