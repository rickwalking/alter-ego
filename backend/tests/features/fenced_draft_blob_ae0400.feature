Feature: A slide draft written as a fenced JSON object becomes its copy (AE-0400)
  Models sometimes answer a slide draft with its bilingual JSON object wrapped
  in a Markdown code fence. The object must be read like an unfenced one, so
  the slide shows the copy and never the raw JSON.

  Scenario: A ```json fenced bilingual draft is normalized
    Given a slide whose draft_text is a ```json fenced object with pt and en heading and body
    When the slide draft is normalized
    Then draft_text is the Portuguese body
    And the pt and en presentations carry their own heading and body

  Scenario: A plain fence without a language tag is read too
    Given a draft wrapped in ``` without a language
    When it is parsed
    Then the bilingual object is returned

  Scenario: JSON literals that Python cannot read are parsed as JSON
    Given a fenced object containing true, false and null
    When it is parsed
    Then the object is returned

  Scenario: Plain copy is left alone
    Given a draft_text that is ordinary slide copy
    When the slide draft is normalized
    Then the slide is unchanged

  Scenario: A broken fenced object is not guessed
    Given a fenced text that is not a valid object
    When it is parsed
    Then nothing is returned and the slide is unchanged

  Scenario: A stringified fenced locale blob resolves to one locale
    Given a fenced object with pt and en strings
    When the visible copy is resolved for en
    Then the English string is returned
