Feature: Custom palette catalog resolution and snapshot (AE-0269)
  As the carousel system
  I want custom palettes resolved over the root+custom union and frozen at generation
  So that user-created palettes render correctly and past carousels stay reproducible
  (ADR-0019: hybrid catalog, snapshot-at-generation D9, mode-derived style D3).

  Background:
    Given the curated root palettes live in the typed registry
    And custom palettes live in the global "palettes" table

  Scenario: A custom palette resolves to its own colours
    Given a custom dark palette referenced by a project's theme (its UUID)
    When the palette is resolved at generation
    Then the resolved colours are the custom palette's colours

  Scenario: A light custom palette never gets a dark image strategy
    Given a custom palette with mode "light"
    When its image style is derived
    Then the style is "flat_editorial" and never a dark neon strategy

  Scenario: The resolver degrades safely when the catalog is unavailable
    Given the palette repository raises an error
    When a root-key themed project is resolved
    Then resolution falls back to the registry and does not fail generation

  Scenario: The carousel snapshots its resolved palette at generation
    Given a project referencing a custom palette
    When the image phase runs for the first time
    Then the resolved palette is frozen onto the project's theme_snapshot
    And the snapshot is persisted

  Scenario: Editing a palette does not change an already-generated carousel
    Given a generated carousel whose theme_snapshot is frozen
    When the underlying custom palette is later edited
    Then the carousel still renders its frozen snapshot colours

  Scenario: Snapshotting is idempotent
    Given a project whose theme_snapshot is already frozen
    When the image phase runs again
    Then the snapshot is not re-resolved or overwritten

  Scenario: AUTO is frozen at first generation
    Given a project with theme "auto" resolved and snapshotted today
    When a new custom palette with overlapping keywords is created later
    Then the project still renders its original frozen palette
