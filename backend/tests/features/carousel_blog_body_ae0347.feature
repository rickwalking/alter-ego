Feature: Carousel blog body is composed from real long-form content (AE-0347)
  Since AE-0032 the public carousel blog is composed from research, outline
  headings and per-slide long_form_notes, but nothing ever produced those
  inputs, so every carousel blog in production was an H1-only stub.

  Scenario: Content prompt requires long-form notes
    Given the v5 carousel content prompt is rendered
    Then it asks the model for long_form_notes in its JSON return contract
    And the content agent renders carousel/content at version v5

  Scenario: Long-form notes survive parsing and reach the slide draft
    Given the model returns draft_text plus long_form_notes
    When the content agent drafts the slide
    Then the draft carries the long_form_notes, case preserved, with markup and
      injection patterns stripped at the source

  Scenario: Model omits long-form notes
    Given the model returns a draft without long_form_notes
    When the content agent drafts the slide
    Then the draft has no long_form_notes
    And one warning naming the slide index is logged, even on a cache hit

  Scenario: English translation carries long-form notes
    Given a PT slide draft with long_form_notes
    When the EN translation payload is built
    Then it includes the PT long_form_notes
    And a draft without slide_index is keyed by its 1-based position
    And the translated long_form_notes are parsed back per slide

  Scenario: Research findings feed the blog intro
    Given research_findings with per-source summaries
    When the distribution pack is built
    Then the blog markdown opens with the de-duplicated summaries

  Scenario: Research findings absent or malformed
    Given research_findings is missing or not a list
    When the intro is derived
    Then it is empty and composition still succeeds

  Scenario: Blog titles derive from the intro slide
    Given a project with no title and no English title
    When the distribution pack is built
    Then the PT title is the heading of the slide whose slide_index is 1,
      even when it is not first in the list
    And the EN title is the translated intro heading

  Scenario: Existing titles are never overwritten
    Given a project that already has a title and an English title
    When the distribution pack is built
    Then both titles are unchanged

  Scenario: Public blog hides carousel blogs whose carousel is not public
    Given a published carousel-origin blog row whose carousel has is_public=false
    When an anonymous client lists or fetches it via /api/public/blog-posts
    Then it is absent from the list and the detail returns 404

  Scenario: Public blog serves carousel blogs once the carousel is public
    Given a published carousel-origin blog row whose carousel has is_public=true
    When an anonymous client lists or fetches it
    Then it is listed and the detail returns 200

  Scenario: Standalone posts are unaffected by the carousel gate
    Given a published standalone blog row
    When an anonymous client fetches it
    Then the detail returns 200
