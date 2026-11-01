Feature: Use the autopilot's generated cover on slide 1 (AE-0590)
  When the cover generation the autopilot started for a fresh carousel
  succeeds, the generated cover becomes slide 1's cover (slide_cover, kind
  ai_image), stored while the workflow is paused at a gate, through the
  lock-version compare-and-set. The owner's choice always wins. The selection
  never re-renders, never changes the carousel status and never publishes;
  the carousel's own finalize render uses the stored cover and the owner
  reviews it as usual. Manual generations keep today's picker flow.

  Scenario: A succeeded autopilot cover becomes slide 1's cover
    Given an autopilot carousel paused at a gate with the default slide 1
    And the autopilot's cover generation succeeded
    When the selection runs
    Then slide_cover is the generated asset with kind ai_image
    And the lock version moved by one

  Scenario: The selection waits for the workflow to pause at a gate
    Given the workflow is running a phase when the generation succeeds
    When the workflow pauses at the next gate
    Then the generated cover is stored only then

  Scenario: The wait gives up after its deadline
    Given the workflow keeps running past the wait deadline
    When the selection runs
    Then nothing is written and the skip is logged with reason timed_out

  Scenario: A cover the owner chose before the job is kept
    Given the carousel was created with the owner's GrokBot cover
    When the autopilot's generation succeeds
    Then slide_cover is unchanged and the skip reason is owner_cover

  Scenario: A manual choice made while the job ran is kept
    Given the owner bound another slide-1 photo while the job ran
    When the autopilot's generation succeeds
    Then slide 1 keeps the owner's photo and the skip reason is manual_choice

  Scenario: A failed generation leaves slide 1 alone
    Given the autopilot's cover generation failed
    When the background run ends
    Then the selection never runs and slide 1 is unchanged

  Scenario: Selecting the same cover twice changes nothing
    Given the generated cover is already slide 1's cover
    When the selection runs again
    Then nothing is written and the outcome is already_selected

  Scenario: A carousel already at the owner's review keeps its cover
    Given the carousel is completed or at final review
    When the autopilot's generation succeeds
    Then slide_cover is unchanged and the cover stays a picker option

  Scenario: The selection never re-renders or publishes
    Given an autopilot carousel paused at a gate
    When the generated cover is stored
    Then no republish, artifact build, status change or publish call happens

  Scenario: A lock-version conflict is skipped and logged, never retried
    Given another writer moved the lock version or holds the project lock
    When the selection writes
    Then nothing is written, the skip reason is conflict and it is not retried

  Scenario: A generated cover whose file is gone is skipped
    Given the generated asset's stored file is gone
    When the selection writes
    Then slide 1 is unchanged and the skip reason is asset_gone

  Scenario: A manual generation is never auto-selected
    Given the owner starts a generation from the publish step
    When it succeeds
    Then slide 1 is unchanged and the cover is only a picker option

  Scenario: An owner photo bound while the write runs is kept
    Given the owner binds another slide-1 photo right before the locked write
    When the selection writes
    Then the owner's photo is kept, slide_cover stays empty and the reason is manual_choice

  Scenario: A lock version moved before the write is a skip
    Given another writer moved the lock version after the selection read it
    When the selection writes
    Then nothing is written and the skip reason is conflict

  Scenario: Binding a slide-1 photo clears an auto-selected cover
    Given slide 1 shows an auto-selected generated cover
    When the owner binds a library photo with PUT hook-photo
    Then slide_cover is cleared and slide 1 shows the owner's photo
