# Carousel content distinctness + rework-feedback adherence (AE-0291)
# Traceability: .agent/tasks/AE-0291-glm-content-prompt-cross-slide-distinctness-and-feedback-adherence.md

Feature: Cross-slide distinctness for GLM content drafting
  As the carousel content pipeline
  I want each slide to see the other slides' outline
  So that GLM produces distinct body copy instead of near-duplicates

  Scenario: Each slide prompt carries the other slides' outline
    Given an outline of three slides
    When the content phase drafts a slide
    Then that slide's prompt includes the OTHER slides' headings and key points
    And it excludes the slide's own heading

  Scenario: A near-duplicate slide is re-drafted once and the distinct copy kept
    Given two slides drafted with near-identical body copy
    When cross-slide distinctness runs
    Then the duplicate slide is re-drafted at most once
    And the more distinct re-draft replaces the near-duplicate

  Scenario: Distinctness metric flags later near-duplicates only
    Given slide bodies where a later body repeats an earlier body
    When duplicate detection runs
    Then the earlier body is kept and the later one is flagged

Feature: Imperative rework feedback adherence
  As an editor sending content back for revision
  I want the model to see rejected copy with imperative instructions
  So that regeneration actually changes the copy per my notes

  Scenario: Reviewer notes render once, imperatively, with the previous draft
    Given a content send-back with reviewer notes and a previous rejected draft
    When the slide instruction context is built
    Then the imperative REGENERATION header appears exactly once
    And the previous rejected draft is included for the model to diff against
    And the notes are not duplicated across the prompt template and instruction

  Scenario: Injecting the previous draft busts the response cache
    Given the same slide regenerated with a different previous draft each time
    When the content agent drafts the slide
    Then the cached rejected response is not returned

Feature: Live model config on the v4 content path
  As the content pipeline
  I want the prompt YAML temperature and max_tokens to reach the model
  So that sampling knobs are no longer silently discarded

  Scenario: The v4 model config is bound on the LLM call
    Given the v4 carousel content prompt with a temperature and max_tokens
    When the content agent drafts a slide
    Then those values are bound on the model runnable for the call
