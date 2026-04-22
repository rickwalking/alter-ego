Feature: LinkedIn post generation with voice cloning
  As a carousel author
  I want a voice-cloned LinkedIn post in PT and EN
  So I can publish my own writing without rewriting it

  Background:
    Given a completed carousel with blog_pt and blog_en populated

  # Voice profile -------------------------------------------------------

  Scenario: Voice samples are loaded from configured URLs
    Given WRITING_STYLE_URLS contains 2 public LinkedIn post URLs
    And the URLs expose og:description meta tags
    When the WritingStyleProfile loads samples
    Then 2 VoiceSample entries are returned
    And each entry carries the preview text and detected language

  Scenario: Voice samples are cached to disk after first load
    When the WritingStyleProfile loads samples for the first time
    Then a cache file is written to writing_style_cache_dir
    And a second load reads from the cache without scraping

  Scenario: Manual samples file wins over URL scraping
    Given config/writing_style_samples.yml exists with 3 full post bodies
    When the WritingStyleProfile loads samples
    Then only the manual samples are returned
    And no scraping is performed

  Scenario: Scrape failures are skipped without failing the load
    Given one URL returns 404 and another returns a valid preview
    When the WritingStyleProfile loads samples
    Then only the successful sample is returned

  Scenario: Empty writing_style_urls still produces a valid profile
    Given WRITING_STYLE_URLS is empty
    When the WritingStyleProfile loads samples
    Then an empty list is returned
    And the generator falls back to a default voice instruction

  # Post generation ----------------------------------------------------

  Scenario: Generates a LinkedIn post in Portuguese from blog_pt
    Given the project has blog_pt populated
    When the generator runs for language "pt"
    Then a LinkedInPost with language="pt" is returned
    And the text is non-empty and <= 3000 chars

  Scenario: Generates a LinkedIn post in English from blog_en
    Given the project has blog_en populated
    When the generator runs for language "en"
    Then a LinkedInPost with language="en" is returned

  Scenario: Missing blog source raises a clear error
    Given the project has no blog_en
    When the generator runs for language "en"
    Then a ValueError is raised mentioning the missing language

  Scenario: Voice examples are injected into the prompt
    Given at least one voice sample is loaded
    When the generator runs
    Then the LLM prompt includes the voice examples block

  Scenario: Post body is truncated on sentence boundary when over limit
    Given the LLM returns text longer than 3000 chars
    When the generator processes the response
    Then the returned text is <= 3000 chars
    And it ends on a sentence or paragraph boundary

  Scenario: Leading "LinkedIn Post:" label is stripped
    Given the LLM returns text prefixed with "LinkedIn Post:"
    When the generator processes the response
    Then the label is removed from the final text

  # Pipeline integration ----------------------------------------------

  Scenario: Phase 8 writes PT and EN posts to the project
    Given the carousel pipeline reaches phase 8
    And the project has both blog_pt and blog_en
    When phase 8 runs
    Then project.linkedin_post_pt is set
    And project.linkedin_post_en is set

  Scenario: Phase 8 is a no-op when the generator is not wired
    Given CarouselAgent is constructed without a LinkedInPostGenerator
    When the pipeline reaches phase 8
    Then the project's LinkedIn fields remain None
    And the pipeline completes successfully
