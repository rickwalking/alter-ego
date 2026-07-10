# AE-0309 — Carousel content drafter must fail closed on scaffold parse failure
Feature: Content drafting fails closed on parse failure
  A per-slide drafting parse failure can never silently store the raw drafting
  scaffold as visible slide copy. The content phase validates its own output at
  write time, repairs deterministically when possible, retries the LLM draft
  once when not, and — as a last resort — surfaces a blocking, user-visible
  validation error at the content step.

  Scenario: Deterministic repair rescues a scaffold-contaminated slide
    Given a slide draft whose PT extraction returns the full drafting scaffold
    When the content phase builds localized slides
    Then the deterministic repair strips the scaffold and trims the body
    And the stored presentation_pt body contains no scaffold labels
    And the payload has the canonical key set

  Scenario: Unrepairable slide surfaces at the content review step
    Given a slide draft that fails extraction, repair, and one retry
    When the content phase interrupts for human review
    Then the interrupt payload carries a blocking violation for that slide
    And the content step UI shows the slide number and violation messages

  Scenario: The single LLM retry rescues an unrepaired slide
    Given a slide draft that fails extraction and deterministic repair
    And the retried LLM draft parses cleanly
    When the content phase builds localized slides
    Then the retried draft's payload is stored with the canonical keys
    And no blocking violation is reported for that slide
    # Test harness: injectable fail-then-succeed draft double (LLM mock)

  Scenario: Clean drafts are unaffected
    Given seven slide drafts that parse cleanly
    When the content phase builds localized slides
    Then no repair or retry runs and the artifact matches today's snapshot

  Scenario: A non-blocking report never consumes the retry or the interrupt
    Given a validation report that carries violations with blocking set to False
    When the fail-closed chain evaluates the content build
    Then the LLM retry is not consumed
    And no blocking content-gate report is attached to the interrupt payload
    # AE-0312 forward-compatibility: warning-severity rules must not fail closed

  Scenario: A locale payload missing canonical keys counts as a parse failure
    Given a content slide draft whose locale payload lacks content_kind and features
    When the content phase builds localized slides
    Then the payload is normalized to carry the canonical key set

  Scenario: Parse failures emit a structured log event with the repair outcome
    Given a slide draft whose PT extraction fails
    When the content phase builds localized slides
    Then a carousel_slide_parse_failed event is logged
    And the event carries project_id, slide_index, locale, and the repair outcome
