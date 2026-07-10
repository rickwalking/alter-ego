Feature: PT sentence-case validation, casing repair, and severity tiers (AE-0312)

  Portuguese carousel copy is held to the same casing bar as English: headings
  and body sentences start uppercase and configured proper nouns (Claude,
  Anthropic) match their canonical casing. Casing rules are warning-severity, so
  they surface in the review panel without blocking approval. The rules and the
  proper-noun list live in the hero_lower_third_v2 policy; a v1 project reports
  no casing violations and receives no casing mutations.

  Background:
    Given a project stamped with presentation policy hero_lower_third_v2

  Scenario: Lowercase PT heading is flagged and repaired
    Given a slide with PT heading "o **espaço mental** privado descoberto no claude"
    When presentation validation runs
    Then heading_not_sentence_case_pt and proper_noun_casing are reported
    And each casing violation is warning-severity
    When the deterministic casing repair runs
    Then the heading becomes "O **espaço mental** privado descoberto no Claude"
    And re-validation reports no casing violations

  Scenario: Second incident heading is repaired preserving markdown
    Given a slide with PT heading "o que os pesquisadores **descobriram**"
    When the deterministic casing repair runs
    Then the heading becomes "O que os pesquisadores **descobriram**"

  Scenario: Body sentence starts are repaired without touching markdown
    Given a PT body "antes de emitir uma única palavra, o modelo constrói algo. uma janela inesperada para a arquitetura do pensamento artificial."
    When the deterministic casing repair runs
    Then both sentences start uppercase and emphasis markers are unchanged

  Scenario: Accented first letters are handled
    Given a slide with PT heading "época dourada"
    When presentation validation runs
    Then heading_not_sentence_case_pt is reported

  Scenario: Exempted slide type keeps stylistic lowercase
    Given a slide type exempted from casing rules in the policy
    When presentation validation runs
    Then no casing violation is reported for that slide

  Scenario: Casing warnings never block approval or trigger fail-closed
    Given a slide whose only violations are warning-severity casing rules
    When the validation report is built
    Then blocking is false
    And the stored report served to the client also has blocking false
    And the content-phase fail-closed chain does not retry or interrupt
    And the reviewer can approve the phase

  Scenario: A blocker alongside a casing warning still blocks
    Given a report containing one casing warning and one blocker violation
    When the validation report is built
    Then blocking is true

  Scenario: Absent severity defaults to blocker
    Given a v2 policy casing rule declared without a severity
    When the policy loads
    Then the load fails

  Scenario: Unknown policy version falls back to v1 without raising
    Given a project stamped with an unsupported presentation policy version
    When the policy loads
    Then it falls back to hero_lower_third_v1 with a warning log

  Scenario: In-flight v1 project is upgraded and re-validated
    Given a final_review-parked project on hero_lower_third_v1 with lowercase PT copy
    When the run-once upgrade migration runs
    Then the project is bumped to hero_lower_third_v2
    And the stored report shows v2 casing warnings immediately
    And a completed project is left untouched

  Scenario: New carousels are stamped v2 while legacy NULL rows keep v1
    Given a new carousel is created
    Then it is stamped hero_lower_third_v2
    And a legacy NULL-version row keeps v1 semantics on re-validation

  Scenario: A v1 project reports no casing violations and gets no casing repair
    Given a project on hero_lower_third_v1 with a lowercase PT heading
    When presentation validation and casing repair run
    Then no casing violation is reported and the heading is left unchanged
