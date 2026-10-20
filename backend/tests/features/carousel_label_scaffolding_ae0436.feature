Feature: Carousel label scaffolding never reaches visible copy (AE-0436)

  The content drafter and the EN translator sometimes echo locale markers and
  field labels into visible slide copy. On prod carousel 7acaf967 the PT body of
  slide 5 shipped "**PT-BR**" and the EN body of slide 7 ended with
  "**CTA creator: radar IA.**", and the content gate reported blocking=false.
  One shared, data-driven detector must drive both the drafter parser (strip at
  the source) and the content gate (a blocking, auto-repairable violation).

  Background:
    Given the carousel presentation contracts hero_lower_third_v4 and pov_hook_v1
    And the AE-0430 content gate and deterministic repair are active

  Scenario: Locale markers in every variant are detected at their scaffold positions
    Given visible slide copy that contains a locale marker
    When the shared label-scaffolding detector runs on the text
    Then it reports the marker for "**PT-BR**", "**PT**", "**EN:**", "**EN-US**",
      "PT-BR:", "PT: Heading:", a bare "PT" line, and "**PT** ** **"

  Scenario: Field labels are detected at their scaffold positions
    Given visible slide copy that contains a drafting field label
    When the shared label-scaffolding detector runs on the text
    Then it reports "Heading:", "Body:", "Title:", "CTA:", "CTA creator:",
      "Summary:", "TL;DR:", "Key points:" and "SLIDE 3:" as bold pairs anywhere
      or plain labels at a line start

  Scenario: A mid-sentence plain label is real copy, not scaffolding
    Given EN copy "The response body: a JSON array."
    And EN copy "TL;DR: o custo caiu 3x."
    And PT copy "Mande o body: JSON com o prompt e o modelo."
    When the shared label-scaffolding detector runs on each text
    Then none of them is flagged
    And the deterministic repair leaves each text unchanged

  Scenario: The drafter strip removes PT-BR markers and PT: Heading: garbage
    Given the prod 5344b6c6 draft "**PT-BR**\nInovação não exige **bilhões**\nA pressão…"
    And the draft "**PT** ** **"
    And the draft "PT: Heading: A versão…"
    When the drafter parser strips scaffold labels
    Then the first body starts with "Inovação não exige"
    And the other two leave no locale marker or field label behind

  Scenario: A bold PT-BR draft builds a clean PT payload
    Given a slide draft whose draft_text starts with "**PT-BR**" followed by
      "**body:**" labels
    When the presentation review builds the localized slides
    Then the PT body contains no "**PT-BR**" and no "**body:**"
    And the PT body starts with the real copy

  Scenario: The content gate flags the prod leaks as blockers
    Given the prod slide 5 PT body "**PT-BR**\nInovação não exige **bilhões**…"
    And the prod slide 7 EN body ending with "**CTA creator: radar IA.**"
    And the prod slide body "PT: Heading:"
    When the localized slides are validated
    Then each leak is a blocking drafting_scaffold_present violation
    And the violation names the exact field and locale

  Scenario: The deterministic repair strips the labels and the gate turns green
    Given a PT body "**PT-BR**\nInovação não exige **bilhões**…"
    And an EN body "Then save this carousel. **CTA creator: radar IA.**"
    When the bounded deterministic repair runs on each payload
    Then the repaired PT body is "Inovação não exige **bilhões**…"
    And the repaired EN body keeps the sentence but drops the CTA creator label
    And re-validating the repaired payloads raises no drafting_scaffold_present

  Scenario: Item texts are label-checked and stripped too
    Given a content slide whose feature body starts with "**Body:**"
    When the localized slides are validated
    Then the feature body is flagged drafting_scaffold_present
    And the deterministic repair strips the label from the item

  Scenario: EN ** emphasis normalizes to <strong> at write time
    Given an EN body "DeepSeek cuts **cost per token** for the same work"
    When the copy is normalized at write time
    Then it becomes "DeepSeek cuts <strong>cost per token</strong> for the same work"

  Scenario: PT <strong> emphasis normalizes to ** at write time
    Given a PT body with "<strong>eficiência</strong>"
    When the copy is normalized at write time
    Then it becomes "**eficiência**"

  Scenario: A surviving emphasis mismatch is a blocker
    Given an EN body with balanced "**cost per token**" emphasis
    And a PT body with "<strong>eficiência</strong>"
    When the localized slides are validated with the v4 policy
    Then each field is a blocking emphasis_markup_locale_mismatch violation
    And the deterministic repair clears both violations

  Scenario: Everything the detector flags is deterministically strippable
    Given every fixture the label detector flags
    When the drafter parser strips scaffold labels from each text
    Then no stripped text is flagged anymore

  Scenario: The translation request sends PT emphasis as <strong>
    Given a PT draft body with "**eficiência**"
    When the EN translation payload is built
    Then the payload carries "<strong>eficiência</strong>"
    And the translation prompt tells the model EN emphasis is <strong>, never **

  Scenario: The policy context never exposes schema field names
    Given the hero_lower_third_v4 policy
    When the presentation policy context renders
    Then it contains no "cta_creator_name", "closing_action_title" or other
      snake_case budget names
    And it says the budget labels are schema identifiers, never visible copy
