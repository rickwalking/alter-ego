Feature: Public carousel images load for anonymous visitors (AE-0412, QA B08)
  Public blog pages showed broken images: the stored hero was an owner-only
  preview URL (401 for visitors) and the public image route only looked in
  the raw images folder, so carousels with rendered slides only returned 404.

  Scenario: A public carousel never exposes preview image URLs
    Given a public carousel whose stored design tokens use "/preview/images/" URLs
    When its design tokens are merged for a response
    Then the hero and every slide list use the public "/images/" route
    And each URL keeps the language of the preview URL

  Scenario: A preview URL without a language maps to Portuguese
    Given a public carousel whose stored hero is a preview URL without "?lang="
    When its design tokens are merged
    Then the hero is the public "/images/" URL with "lang=pt"

  Scenario: Draft carousels keep owner-only preview URLs
    Given a draft carousel with rendered slides
    When its design tokens are merged
    Then the hero is still the owner-only preview URL

  Scenario: Public image route serves the raw image first
    Given a public carousel with a raw image "images/slide_1.jpg" and a rendered "pt/slide_1.jpg"
    When an anonymous visitor GETs "/images/slide_1.jpg"
    Then the raw image is returned

  Scenario: Public image route falls back to the rendered slide of the language
    Given a public carousel with only rendered "en/slide_1.jpg"
    When an anonymous visitor GETs "/images/slide_1.jpg?lang=en"
    Then the rendered English slide is returned

  Scenario: Public image route falls back to the HD rendered slide
    Given a public carousel with only "pt/hd/slide_1.jpg"
    When an anonymous visitor GETs "/images/slide_1.jpg"
    Then the HD slide is returned

  Scenario: Missing image still returns 404
    Given a public carousel without "slide_9.jpg" anywhere
    When an anonymous visitor GETs "/images/slide_9.jpg"
    Then the response is 404

  Scenario: Draft carousel images stay private
    Given a draft carousel with rendered slides
    When an anonymous visitor GETs "/images/slide_1.jpg"
    Then the response is not 200
