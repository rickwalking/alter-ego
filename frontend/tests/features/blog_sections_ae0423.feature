Feature: Public blog renders the v2 document (AE-0423)
  The public detail page renders the post's own cover and per-section images
  with the stored alt text, once only, and never reads carousel design for
  images. It is a pure v2 render with no frontend v1 parser: the backend read
  fail-safe (AE-0423) adapts a non-migrated row before this API, and that
  adapter is removed in AE-0428.

  Background:
    Given an anonymous visitor
    And a published post whose content is schema "blog.v2"

  Scenario: The cover renders as the article hero
    Given the document has a cover with url and non-empty alt
    When the visitor opens /blog/{id}
    Then the hero image src is the cover url
    And the hero image alt is the stored alt

  Scenario: A missing cover uses a neutral default
    Given the document's cover is null
    When the visitor opens /blog/{id}
    Then a neutral default hero is shown
    And the article still renders

  Scenario: Each section renders its own heading, body and image
    Given two sections each with a heading, body_md and an image with alt
    When the visitor opens /blog/{id}
    Then each section shows its heading and body text
    And each section image uses its own url and stored alt

  Scenario: A section without an image renders text only
    Given a section whose image is null
    When the visitor opens /blog/{id}
    Then that section shows its heading and body text
    And no placeholder broken image is shown

  Scenario: No carousel slide image is ever used
    Given the carousel project exposes rendered slides
    When the visitor opens /blog/{id}
    Then no image src contains "/slide-images/"
    And no image url is taken from the carousel design

  Scenario: The title renders exactly once
    Given the stored document has no leading "# " in any section body
    When the visitor opens /blog/{id}
    Then the page contains exactly one H1 with the post title
    And no section renders an H1

  Scenario: Outstanding section image alt is never empty in the DOM
    Given a section image whose stored alt is "Diagrama do fluxo"
    When the visitor opens /blog/{id}
    Then the rendered <img> alt is "Diagrama do fluxo"

  Scenario: Markdown is rendered through the sanitizing allow-list
    Given a section body containing a raw <script> tag
    When the visitor opens /blog/{id}
    Then the script tag is not executed
    And the body renders through the react-markdown allow-list

  Scenario: An unpublished v2 post is not publicly viewable
    Given a v2 post with status "draft"
    When the visitor opens /blog/{id}
    Then the page returns not-found

  Scenario: The public read never fetches carousel blog markdown
    Given a published carousel-origin post with a v2 document
    When the visitor opens /blog/{id}
    Then the app does not call GET /api/carousels/{id}/blog for content
    And it does not take article text from fetchBlogWithDesign
    And it renders only the v2 sections

  Scenario: A carousel-origin post with no v2 row is 404
    Given a carousel with a project_id but no non-deleted blog_posts row
    When the visitor opens /blog/{project_id} or /blog/{id}
    Then the page returns not-found
    And it does not resurrect legacy markdown from the carousel

  Scenario: The listing card uses a fallback when the cover is null
    Given a published v2 post with cover null
    When the listing/dashboard card renders
    Then the card uses a deterministic neutral fallback
    And it never uses a carousel slide image

  Scenario: A non-v2 content blob is rejected by the parse helper
    Given a post whose content has no schema field
    When the public page parses the content
    Then the parse helper rejects it (no legacy fallback)
    And the page fails safe rather than rendering garbage

  Scenario: An English translation renders under the en locale
    Given the document has content.translations.en with its own sections
    When a visitor loads the en locale
    Then the English sections render
    And a missing en translation falls back to the PT sections

  Scenario: A blank translation falls back to PT
    Given content.translations.en has no section with a non-empty body
    When a visitor loads the en locale
    Then the PT sections render (never an empty EN page)

  Scenario: PT/EN content buttons switch the rendered document
    Given a published post with PT and EN documents
    When a visitor clicks "EN" on the post
    Then the page shows the EN cover and sections and sets ?lang=en
    When the visitor clicks "PT"
    Then the page shows the original PT document
    And the UI locale (next-intl) is unchanged
