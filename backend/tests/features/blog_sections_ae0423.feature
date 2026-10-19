Feature: Blog document model (blog.v2), strict parser and one-shot cutover (AE-0423)
  A blog post owns a versioned, section-structured document in blog_posts.content.
  A one-shot backend command (not Alembic) rewrites v1 rows, including every string
  translation. blog.v2 is the ONLY persisted shape: writes are strict and there is no
  legacy write path. Until --verify passes, reads have a temporary text-only fail-safe.

  Background:
    Given a blog_posts row whose content is validated by BlogDocumentService

  # --- Parsing the document shape (strict) ---

  Scenario: A valid blog.v2 document parses to cover + ordered sections
    Given content with schema "blog.v2"
    And a cover image and three ordered sections with stable ids
    When parse_blog_content is called
    Then it returns the cover and the three sections in order
    And each section carries its own stable id, heading, body_md and image

  Scenario: A non-migrated legacy row is read through the temporary fail-safe
    Given a public row whose content is legacy markdown (no schema)
    When the public projection reads it
    Then it renders as a text-only blog.v2 document (cover null, images null, quality null)
    And no carousel slide image is used
    And the blog_v2_non_migrated_rows metric is emitted
    And no 500 is returned

  Scenario: Writes remain strict while the read fail-safe is active
    Given a legacy markdown row
    When BlogDocumentService.save is called with the legacy shape
    Then it raises InvalidBlogDocumentError
    And nothing is persisted

  Scenario: An in-progress draft may have zero sections and a null quality
    Given content with schema "blog.v2", sections [] and quality null
    And generation.status is "in_progress"
    When parse_blog_content is called
    Then it returns the empty draft document
    But publish validation rejects it (at least one non-empty section is required)

  Scenario: A section image with an empty alt is rejected on write
    Given a blog.v2 document whose section image has alt ""
    When BlogDocumentService.save is called
    Then it raises a validation error (422)
    And nothing is persisted

  Scenario: Duplicate section ids are rejected
    Given a blog.v2 document with two sections that share an id
    When BlogDocumentService.save is called
    Then it raises a validation error (422)

  Scenario: A non-v2 write shape is rejected, never coerced
    Given content that is a flat markdown string (no schema)
    When parse_blog_content is called for a write
    Then it raises InvalidBlogDocumentError
    And no section is synthesized from the string

  Scenario: Malformed JSONB is rejected
    Given content that is a JSON array instead of a document object
    When parse_blog_content is called
    Then it raises InvalidBlogDocumentError

  # --- One-shot cutover command (PT + translations) ---

  Scenario: A v1 row is cut over in place and the old shape is dropped
    Given a v1 row whose markdown opens with "# GPT 5.6 saiu" then two "## " sections
    When the cutover runs with --apply
    Then content schema becomes "blog.v2"
    And the leading H1 is stripped and its now-empty lede chunk is discarded
    And the row has exactly two sections with fresh sec_<uuid4> ids
    And cover is null, quality is null and every section image is null
    And featured_image_url is null
    And the flat markdown is not retained on the row

  Scenario: Every string translation is cut over with the same rules
    Given a v1 row with content.translations {"en": "# Title\n\n## What happened\n\nBody"}
    When the cutover runs with --apply
    Then content.translations.en is a blog.v2 document
    And it has one section with heading "What happened" and body "Body"
    And the top-level translations value is no longer a string

  Scenario: A non-string translation entry is dropped, not stringified
    Given a v1 row whose content.translations contains a dict for "en"
    When the cutover runs with --apply
    Then the row has no translations.en document
    And no body_md contains "{'"

  Scenario: A "## " line inside a fenced code block is not a section boundary
    Given a v1 row whose markdown contains a fenced block with a "## comment" line
    When the cutover runs with --apply
    Then the fenced block stays inside its section body
    And the row has the expected unordered section count

  Scenario: A non-markdown content object does not become str(dict) garbage
    Given a v1 row whose content is a dict without a markdown/body key
    When the cutover runs with --apply
    Then the row has exactly one empty section
    And the section body_md does not contain "{'"

  Scenario: The cutover stores the raw body without sanitizing
    Given a v1 row whose section body contains HTML entities and markdown constructs
    When the cutover runs with --apply
    Then the stored body_md equals the original section body bytes

  Scenario: The cutover is idempotent
    Given a row already at schema "blog.v2"
    When the cutover runs with --apply a second time
    Then the row is unchanged (byte-identical content, same section ids)

  Scenario: --dry-run reports rows and changes nothing
    Given a table with one v1 row that has PT and EN bodies
    When the cutover runs with --dry-run
    Then it reports counts for the row and both bodies
    And every row's content is byte-identical to before

  Scenario: An H1-only stub migrates to a single section
    Given a v1 row whose markdown is only "# A title with no body"
    When the cutover runs with --apply
    Then the row has exactly one section
    And that section's body_md is empty
    And the document is valid (schema "blog.v2")

  Scenario: An empty or malformed v1 body still yields a valid document
    Given a v1 row whose content is null
    When the cutover runs with --apply
    Then the row has exactly one empty section
    And the document parses as valid blog.v2

  Scenario: --rollback re-joins sections to text-equivalent markdown
    Given a cut-over blog.v2 row with two headed PT sections and one EN translation
    When the cutover runs with --rollback from the new image before the code is reverted
    Then the flat PT markdown equals "## heading" + the original body bytes
    And translations.en is restored to its original flat markdown
    And the title H1 is not restored (it lives in the title column)

  Scenario: --verify gates on zero non-v2 rows
    Given a blog_posts table containing at least one pre-cutover row
    When the cutover runs with --apply --verify
    Then the command exits zero and finds zero rows (and translations) not at schema "blog.v2"

  Scenario: --verify exits non-zero on a non-v2 row
    Given a blog_posts table with one row left at the legacy shape
    When the cutover runs with --verify
    Then the command exits non-zero
    And the deploy aborts before the app stack starts

  Scenario: The deploy runs the cutover after Postgres and before the app stack
    Given the deploy workflow has built the new image and stopped the old stack
    When Postgres becomes healthy
    Then the cutover runs with --apply --verify using the new image
    And the full stack starts only after a zero exit

  # --- featured_image_url projection ---

  Scenario: featured_image_url tracks cover.url on save
    Given a blog.v2 document whose cover.url is "https://cdn/x.jpg"
    When BlogDocumentService.save is called
    Then featured_image_url equals "https://cdn/x.jpg" in the same transaction

  Scenario: Removing the cover clears featured_image_url
    Given a blog.v2 document whose cover was set
    When the cover is removed and the document is saved
    Then cover is null
    And featured_image_url is null

  Scenario: A null cover does not block publish and cards use a fallback
    Given an approved blog.v2 post with cover null
    When it is published
    Then the post is published
    And the listing card/OG uses the deterministic fallback, never a carousel slide

  # --- Public render contract (backend payload) ---

  Scenario: A published v2 post serializes its own section images
    Given a published blog.v2 post with a cover and per-section images
    When an anonymous client GETs /api/public/blog-posts/{id}
    Then each section image url and its non-empty alt are present in the payload
    And no url references a /slide-images/ path

  Scenario: The public payload is a projection without internal fields
    Given a published blog.v2 post with quality scores and image prompts
    When an anonymous client GETs /api/public/blog-posts/{id}
    Then the payload has no quality, no image.prompt and no image.model
    And translations.en has its own quality, which is also editor-only

  Scenario: EN is gated like PT
    Given the writer produced translations.en.sections
    When the quality gate runs
    Then the same voice/repetition checks run on the EN sections
    And translations.en.quality stores the EN score
