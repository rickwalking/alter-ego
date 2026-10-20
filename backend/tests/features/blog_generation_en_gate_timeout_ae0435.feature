Feature: Blog generation keeps a finished article and never stores Portuguese as English (AE-0435)

  # Prod 2026-10-19/20 (QA report 2026-10-19, F-01 / F-02):
  # - F-01: post ba37f6f9 failed at exactly started_at + 900 s (generation_timeout,
  #   0 of 7 images) although its article was stored; 10-image posts finish their
  #   images 6 s under the same wall. One global budget covered the writer, both
  #   gates and every image.
  # - F-02: content.translations.en of ba37f6f9 and 99886e71 is Portuguese. The EN
  #   gate scored it 85 (voice/repetition only): the PT persona scorer suggested
  #   Portuguese wording, the judge forwarded it and the EN rewrite wrote Portuguese.

  Background:
    Given a from-carousel generation of a post with 4 sections

  # --- F-01: stage budgets ------------------------------------------------------

  Scenario: The images stage has its own budget, sized by the slot count
    Given the text stage finishes within BLOG_GENERATION_TEXT_TIMEOUT_SECONDS
    And the image concurrency is 2 and 5 image slots are empty
    When the images stage starts
    Then its budget is 3 waves of BLOG_IMAGE_WAVE_TIMEOUT_SECONDS
    And the time the text stage took is not taken from the images budget

  Scenario: A text stage that runs out of time fails the run as before
    Given the writer never answers within BLOG_GENERATION_TEXT_TIMEOUT_SECONDS
    When the text budget runs out
    Then the run finishes "failed" with "generation_timeout" and recoverable true
    And nothing is stored as the article

  Scenario: An images stage that runs out of time keeps the finished images
    Given the article is stored
    And 2 image slots finish and the other slots never finish within the images budget
    When the images budget runs out
    Then the 2 finished images are attached to the stored article
    And every unfinished slot has an "image_timeout" error naming the slot
    And the run finishes "partial" with recoverable true

  Scenario: A partial run after an images timeout resumes images-only
    Given a run finished "partial" after an images timeout
    When the owner retries the generation
    Then only the empty image slots are generated
    And the article is not rewritten

  # --- F-02: deterministic EN language gate --------------------------------------

  Scenario: An English translation passes the language gate unchanged
    Given the writer's EN sections are written in English
    When the article is gated
    Then translations.en holds the writer's EN sections
    And no EN retranslation is requested

  Scenario: Portuguese EN sections are retranslated from the gated PT article
    Given the writer's EN sections are written in Portuguese
    When the article is gated
    Then the EN wrong-language check flags them without calling a model
    And the gated PT sections are translated to English
    And translations.en holds the English translation with the PT section ids

  Scenario: The retranslation is bounded and never stores Portuguese as English
    Given the writer's EN sections are written in Portuguese
    And every retranslation also comes back in Portuguese
    When the article is gated
    Then at most BLOG_EN_MAX_RETRANSLATIONS retranslations are requested
    And the stored article has no translations.en
    And the run finishes "partial" with an "en_translation_wrong_language" error and recoverable true
    And the images are still generated

  Scenario: A failed retranslation call counts as one attempt
    Given the writer's EN sections are written in Portuguese
    And the first retranslation call fails and the second returns English
    When the article is gated
    Then translations.en holds the second retranslation

  # --- F-02 root cause: the EN rewrite pass -------------------------------------

  Scenario: An EN rewrite that switches to Portuguese is discarded
    Given the writer's EN sections are English but fail the voice gate
    And the rewrite pass returns Portuguese sections
    When the EN language is gated
    Then the English sections from before the rewrite are kept
    And their rewrite_passes is 1

  Scenario: The judge and the rewrite are told the language to keep
    Given the EN article failed the voice gate
    When the judge and the rewrite prompts are rendered
    Then both name English as the only output language
    And both say to ignore suggestions that switch the language

  # --- the editor's "Generate EN translation" -----------------------------------

  Scenario: The editor translation refuses a Portuguese answer
    Given the owner asks for the EN translation of a post
    And the model answers a section in Portuguese
    When the translation is built
    Then it fails with "blog_translation_wrong_language"
    And nothing is stored as translations.en

  # --- one-shot repair of existing posts ----------------------------------------

  Scenario: The scan lists posts whose EN reads as Portuguese (read-only)
    Given stored posts where one translations.en reads as Portuguese
    When the operator runs regenerate_blog_en without --apply
    Then it lists that post and its Portuguese EN sections
    And nothing is written

  Scenario: --apply regenerates only the EN of the named post
    Given a stored post whose translations.en reads as Portuguese
    When the operator runs regenerate_blog_en --apply --only that post
    Then translations.en is replaced by an English translation of the PT sections
    And the PT sections, the images and the cover are unchanged
    And a version snapshot of the previous content is recorded

  Scenario: --apply leaves an English EN untouched
    Given a stored post whose translations.en is English
    When the operator runs regenerate_blog_en --apply --only that post
    Then the post is reported as skipped and nothing is written
