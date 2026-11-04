Feature: The EN heading-case allowlist applies to the first visible word (AE-0612)

  An EN heading must start with an uppercase letter, unless it opens with an
  intentionally lowercase token from the policy allowlist (iPhone, eBay, macOS).
  The token is matched as a whole word, case-sensitively, on the first word the reader
  sees: tags around it do not hide it. The allowlist itself does not change, and
  neither the check nor the repair ever rewrites an allowlisted token or a tag.

  Scenario: An allowlisted token wrapped in a strong tag passes
    Given an EN heading "<strong>iPhone</strong> tips"
    When presentation validation runs
    Then heading_not_sentence_case_en is not reported

  Scenario: An allowlisted token under nested tags passes
    Given an EN heading "<strong><em>eBay</em></strong> tips"
    When presentation validation runs
    Then heading_not_sentence_case_en is not reported

  Scenario: A plain heading that opens with an allowlisted token passes
    Given an EN heading "iPhone tips"
    When presentation validation runs
    Then heading_not_sentence_case_en is not reported

  Scenario: A heading that is only an allowlisted token still passes
    Given an EN heading "macOS"
    When presentation validation runs
    Then heading_not_sentence_case_en is not reported

  Scenario: A heading that has no visible text has no opening token
    Given an EN heading "<strong></strong>"
    When presentation validation runs
    Then heading_not_sentence_case_en is not reported

  Scenario: A plain lowercase heading still fires
    Given an EN heading "word that matters"
    When presentation validation runs
    Then heading_not_sentence_case_en is reported

  Scenario: A lowercase word wrapped in a strong tag still fires
    Given an EN heading "<strong>word</strong> that matters"
    When presentation validation runs
    Then heading_not_sentence_case_en is reported

  Scenario: The allowlist match stays case-sensitive
    Given an EN heading "<strong>iphone</strong> tips"
    When presentation validation runs
    Then heading_not_sentence_case_en is reported

  Scenario: A token that is only the prefix of a longer word still fires
    Given an EN heading "iPhoneX tips"
    When presentation validation runs
    Then heading_not_sentence_case_en is reported

  Scenario: A token that is only the prefix of a wrapped longer word still fires
    Given an EN heading "<strong>eBayer</strong> tips"
    When presentation validation runs
    Then heading_not_sentence_case_en is reported

  Scenario: A token after the first visible word is not an opening token
    Given an EN heading "5 iPhone tips"
    When presentation validation runs
    Then heading_not_sentence_case_en is reported

  Scenario: The repair leaves a wrapped allowlisted heading as it is
    Given an EN heading "<strong>iPhone</strong> tips" and a lowercase item title on the same slide
    When the deterministic repair runs on the reported violations
    Then the heading is still "<strong>iPhone</strong> tips"

  Scenario: The repair still fixes a lowercase heading next to a lowercase item title
    Given an EN heading "<strong>word</strong> that matters" and a lowercase item title on the same slide
    When the deterministic repair runs on the reported violations
    Then the heading is "<strong>Word</strong> that matters"

  Scenario: The EN export keeps an allowlisted token in the heading and the body
    Given a slide whose EN translation has the heading "<strong>iPhone</strong> tips" and the body "iPhone owners win."
    When the EN render source is built with the policy allowlist
    Then the heading and the body are unchanged

  Scenario: The EN export still sentence-cases other lowercase copy
    Given a slide whose EN translation has the heading "<strong>word</strong> that matters" and the body "detail here."
    When the EN render source is built with the policy allowlist
    Then the heading is "<strong>Word</strong> that matters" and the body is "Detail here."
