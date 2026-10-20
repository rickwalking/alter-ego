Feature: Blog editor versions keep the original draft and surface errors (AE-0438)
  The version history of a generated blog post never contains the empty bootstrap
  document: the first stored version is the first stored AI draft and restoring it
  works. A single-section voice rewrite never duplicates the heading into the body,
  and a one-shot operator command reports and repairs posts whose history still
  holds an empty snapshot from the pre-fix era.

  Background:
    Given an editor authenticated as EditorUser

  # --- versions: the first version is the first AI draft (F-05) ---

  Scenario: Generation's first write does not snapshot the empty bootstrap
    Given a draft row with the bootstrap blog.v2 document (zero sections)
    When the generation run stores the first AI-written article
    Then version_history has no entry for the bootstrap
    And the post content holds the article

  Scenario: The first appended version is the first stored AI draft
    Given the generation run stored the article without a snapshot
    When the next content write (an image attach or an owner save) commits
    Then version_history has exactly one entry numbered 1
    And its snapshot equals the article the generation stored
    And restoring version 1 succeeds (it validates as a non-empty document)

  Scenario: No write ever snapshots an empty document
    Given the owner cleared every section body and cover
    When the owner saves that empty document
    Then no version entry is appended for the empty state
    And the previous history is unchanged

  Scenario: History stays bounded and de-duplicated with the empty-skip rule
    Given more than BLOG_VERSION_HISTORY_MAX saves
    Then the first entry and the newest entries are kept
    And a write whose pre-state equals the newest entry appends nothing

  Scenario: Restoring a pre-fix empty snapshot answers a specific 422
    Given a stored version 1 whose snapshot is the empty bootstrap (pre-fix data)
    When the editor POSTs /blog-posts/{id}/restore-version/1 with If-Match
    Then the API responds 422 with detail "blog_version_empty"
    And the post content is unchanged

  # --- versions: operator command for existing posts ---

  Scenario: The count command reports posts whose history holds empty snapshots
    Given post A whose history holds the empty bootstrap as version 1
    And post B whose history starts with the article
    When the operator runs blog_empty_versions --count
    Then post A is listed with one empty entry
    And post B is not listed
    And no row is written

  Scenario: The apply command drops empty entries and renumbers idempotently
    Given post A whose history is [empty v1, article v2, edit v3]
    When the operator runs blog_empty_versions --apply
    Then the history is renumbered to [article v1, edit v2]
    And a second run changes nothing
    And verify exits 0

  # --- single-section rewrite: no heading echo (F-08) ---

  Scenario: A bold heading echoed into the rewrite result is stripped
    Given section sec_1 with heading "Planilha vence torcida"
    And the persona rewrite returns "**Planilha vence torcida**\n\nMinha cadência é mensal"
    When the editor POSTs /blog-posts/{id}/sections/sec_1/rewrite
    Then sec_1.body_md is "Minha cadência é mensal"

  Scenario: A markdown or plain heading echo is stripped too
    Given section sec_1 with heading "Planilha vence torcida"
    And the persona rewrite returns "# Planilha vence torcida\n\nMinha cadência"
    When the editor POSTs /blog-posts/{id}/sections/sec_1/rewrite
    Then sec_1.body_md is "Minha cadência"
    And a plain "Planilha vence torcida" first line is stripped the same way

  Scenario: A body that starts differently is kept untouched
    Given section sec_1 with heading "Planilha vence torcida"
    And the persona rewrite returns "A planilha vence a torcida.\n\nMinha cadência é mensal"
    When the editor POSTs /blog-posts/{id}/sections/sec_1/rewrite
    Then sec_1.body_md starts with "A planilha vence a torcida."

  Scenario: The rewrite request tells the model not to repeat the heading
    Given section sec_1 with heading "Planilha vence torcida"
    When the editor POSTs /blog-posts/{id}/sections/sec_1/rewrite
    Then the persona enforce prompt instructs the model to return only the body
    And not to repeat the heading

  Scenario: A rewrite of a section without a heading is not altered
    Given section sec_1 without a heading
    And the persona rewrite returns "Minha cadência é mensal"
    When the editor POSTs /blog-posts/{id}/sections/sec_1/rewrite
    Then sec_1.body_md is "Minha cadência é mensal"
