Feature: The EN heading-case check reads the first visible letter (AE-0605)

  An EN heading must start with an uppercase letter. Inline tags are emphasis, not
  copy, so the check looks past them to the first letter the reader sees. The tags
  themselves stay in the content, and the repair keeps them intact.

  Scenario: A heading that starts with a strong tag and an uppercase letter passes
    Given an EN heading "<strong>Word</strong> that matters"
    When presentation validation runs
    Then heading_not_sentence_case_en is not reported

  Scenario: Nested tags before an uppercase letter pass
    Given an EN heading "<strong><em>Word</em></strong> that matters"
    When presentation validation runs
    Then heading_not_sentence_case_en is not reported

  Scenario: A closing tag and whitespace before an uppercase letter pass
    Given an EN heading "  </em> <strong>Word</strong> that matters"
    When presentation validation runs
    Then heading_not_sentence_case_en is not reported

  Scenario: A heading that is only markup has no letter to check
    Given an EN heading "<strong></strong>"
    When presentation validation runs
    Then heading_not_sentence_case_en is not reported

  Scenario: A plain lowercase heading still fires
    Given an EN heading "word that matters"
    When presentation validation runs
    Then heading_not_sentence_case_en is reported

  Scenario: A lowercase heading wrapped in a strong tag still fires
    Given an EN heading "<strong>word</strong> that matters"
    When presentation validation runs
    Then heading_not_sentence_case_en is reported

  Scenario: A lowercase heading under nested tags still fires
    Given an EN heading "<strong><em>word</em></strong> that matters"
    When presentation validation runs
    Then heading_not_sentence_case_en is reported

  Scenario: A non-letter first character keeps its current result
    Given an EN heading that opens with a digit or a quote
    When presentation validation runs
    Then the first letter after it decides the result, as before

  Scenario: The rule stays EN-only
    Given a PT heading "<strong>palavra</strong> que importa"
    When presentation validation runs
    Then heading_not_sentence_case_en is not reported

  Scenario: The repair capitalizes the visible letter and keeps the tag
    Given an EN heading "<strong>word</strong> that matters"
    When the deterministic repair runs on its violations
    Then the heading becomes "<strong>Word</strong> that matters"
    And heading_not_sentence_case_en is not reported on re-validation

  Scenario: An already correct wrapped heading is left as it is
    Given an EN heading "<strong>Word</strong> that matters"
    When presentation validation and the deterministic repair run
    Then the heading stays "<strong>Word</strong> that matters"
