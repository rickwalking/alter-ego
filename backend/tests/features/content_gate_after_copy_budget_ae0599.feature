Feature: Generated copy passes the content gate after the copy budget step (AE-0599)

  After the AE-0588 deploy (2026-11-02 13:31Z) 3 of 3 autopilot carousels were
  blocked at the content gate; the 12 gates before it had 0 violations. The
  first gate of 6f36130e had 31 violations and d8da820a 39: body_too_long and
  heading_too_long in PT and EN plus emphasis_markup_locale_mismatch on EN,
  every one of them on a slide whose draft came back as a bilingual blob
  (heading, body and items in PT and EN, the EN written by the drafting model
  with the PT ** markers). The fix is on the generation side only: the content
  gate, its limits, the voice threshold of 70, the forbidden phrases and the
  ADR-0030 checks are unchanged.

  Background:
    Given the "pov_hook_v1" contract sized to a 9-slide deck
    And a fit model double that rewrites each requested field inside its limit
    And keeps the emphasis markers of the text it was given

  # --- A: emphasis is measured and written in each locale's convention -------

  Scenario: EN copy with PT emphasis markers is converted before it is measured
    Given a bilingual blob slide whose EN item titles use ** emphasis
    And the <strong> tags would push two of those titles over their 32 characters
    When the copy budget step runs
    Then the EN titles reach the shorten model already in <strong> emphasis
    And the slide's EN copy carries no ** marker
    And no field is over its budget

  Scenario: A fit answer in the other locale's markers is converted before it is checked
    Given an over-budget EN body with <strong> emphasis
    And the fit model answers it with ** emphasis
    When the copy budget step runs
    Then the accepted EN body uses <strong> emphasis

  Scenario: The owner's hook heading keeps its markers
    Given the hook slide's PT heading is the owner's chosen hook and uses <strong>
    When the copy budget step runs
    Then the PT hook heading is unchanged
    And the EN hook heading's ** emphasis becomes <strong>

  # --- B: the three blocked prod shapes reach the gate clean ---------------

  Scenario Outline: A blocked prod shape passes the content gate after the step
    Given the drafts and translations of the "<shape>" shape, synthetic text
    When the copy budget step runs and the content review is built
    Then the content gate has no violation

    Examples:
      | shape    |
      | 6f36130e |
      | d8da820a |

  Scenario Outline: With the shorten model down the gate still blocks, on length only
    Given the drafts and translations of the "<shape>" shape, synthetic text
    And the fit model fails
    When the copy budget step runs and the content review is built
    Then the content gate blocks
    And every violation is a length violation, none an emphasis mismatch

    Examples:
      | shape    |
      | 6f36130e |
      | d8da820a |

  Scenario: The quote card keeps the same shape in PT and EN through the step
    Given the "41c4f437" shape, whose slide 5 carries a quote card in PT and EN
    And whose slide 4 EN translation kept a quote card its PT draft lost
    When the copy budget step runs and the content review is built
    Then slide 5 has the insight in both locales
    And the gate reports no violation

  # --- C: the drafting prompts put this slide's limits next to the role ------

  Scenario: The POV content prompt carries this slide's contract limits inline
    Given slide 7 of a 9-slide POV deck, role twist
    When the content prompt is rendered for that slide
    Then it contains this slide's body limit from the contract
    And the limits sit before the answer format

  Scenario: The slide limits block no longer asks for English copy
    When the slide limits block is rendered for a content slide
    Then it no longer says the limits apply to "the English copy" as a given
    And it says a listed item limit is not a request to add items
    And it states the markup cost of <strong> emphasis in English

  Scenario: The default prompt versions are the new ones
    Then the POV content prompt default is v4
    And the slide limits prompt default is v2
    And the earlier versions are kept for rollback

  # --- D: the step says why a rewrite was dropped ------------------------------

  Scenario: The done log counts the dropped rewrites by reason
    Given a fit answer that is not shorter and one that adds a violation
    When the copy budget step runs
    Then the done log reports one "not_shorter" and one "new_violation"

  Scenario: A voice revert is logged with its slides
    Given a shortened slide whose voice score falls from 80 to 60
    When the copy budget step runs
    Then the slide goes back to its pre-shortening copy
    And a voice revert log names that slide
