Feature: Presentation byte-identical safety net (AE-0116)
  As the Phase 5 modularization effort
  I want a byte-identical baseline for the presentation surface
  So that moving routes/services/persistence behind a facade cannot silently
  change a response schema, an artifact's bytes/content-type, or an artifact path

  Background:
    Given a completed carousel with deterministic design tokens, blog
      translations, DB slides, and on-disk artifact files staged with fixed bytes
    And DEBUG and the env-sensitive presentation settings are pinned

  # --- JSON responses (golden snapshots) ---------------------------------------

  Scenario: design response unchanged for a rendered public carousel
    Given a rendered public carousel
    When GET /api/carousels/{id}/design runs
    Then the response matches the committed snapshot

  Scenario: design route rejects a non-public carousel
    Given a non-public carousel
    When GET /api/carousels/{id}/design runs
    Then the response status is 404

  Scenario: default blog response unchanged
    Given a public carousel with a generated blog
    When GET /api/carousels/{id}/blog runs
    Then the response matches the committed snapshot

  Scenario: i18n blog response unchanged for a translated language
    Given a public carousel with a translated blog
    When GET /api/carousels/{id}/blog/{lang} runs
    Then the response matches the committed snapshot
    And the available languages list is byte-identical

  Scenario: slides list response unchanged for the owner
    Given an owner-owned carousel with persisted slides
    When GET /api/carousels/{id}/slides runs as the owner
    Then the response matches the committed snapshot

  Scenario: slides list is forbidden for a non-owner editor
    Given an owner-owned non-public carousel
    When GET /api/carousels/{id}/slides runs as a non-owner editor
    Then the response status is 403

  Scenario: strategy listing response unchanged
    When GET /api/carousels/strategies runs
    Then the response matches the committed snapshot

  Scenario: creator-asset upload response unchanged
    Given a deterministic fixed-bytes PNG and no live image provider
    When POST /api/carousels/{id}/creator-asset/upload runs as the owner
    Then the response matches the committed snapshot
    And the normalized media type, width, and height are byte-identical

  # --- FileResponse endpoints (content-type + headers + byte digest) -----------

  Scenario: pdf bytes + headers + content-type unchanged
    Given a built carousel PDF staged with fixed bytes
    When GET /api/carousels/{id}/pdf runs
    Then the content-type, content-disposition, and byte digest match the snapshot

  Scenario: per-language pdf serves the language-specific bytes
    Given per-language carousel PDFs staged with distinct fixed bytes
    When GET /api/carousels/{id}/pdf?lang=en runs
    Then the served byte digest is the en-specific digest

  Scenario: hero image bytes + content-type + cache headers unchanged
    Given a staged shared hero image with fixed bytes
    When GET /api/carousels/{id}/images/{filename} runs
    Then the content-type, cache headers, and byte digest match the snapshot

  Scenario: per-language slide image serves the language-specific bytes
    Given per-language rendered slide images staged with distinct fixed bytes
    When GET /api/carousels/{id}/slide-images/{lang}/{filename} runs
    Then the served byte digest is the language-specific digest

  Scenario: download lists the staged artifact relative paths
    Given a carousel with staged artifacts under its output dir
    When GET /api/carousels/{id}/download runs as the owner
    Then the response lists the artifact relative paths and omits the output dir

  # --- Falsifiability ----------------------------------------------------------

  Scenario: a one-byte artifact mutation changes the asserted digest
    Given a built carousel PDF
    When the served bytes are compared to a one-byte-mutated copy
    Then the digests differ

  Scenario: the snapshot diff is non-empty for a mutated response
    Given a committed blog snapshot that matches the live response
    When a field of the parsed snapshot is mutated
    Then the equality check used by the safety net rejects the mutation
