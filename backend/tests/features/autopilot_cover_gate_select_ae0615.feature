Feature: The autopilot puts its succeeded cover on slide 1 at the next gate (AE-0615)
  The background selection waits for the workflow to pause, but the
  autopilot drive approves each gate and starts the next phase at once, so
  it never sees a pause: the first settled state it reads is the final
  review, where it must skip. Its conflict is never retried, and a restart
  (a deploy) loses it. So the owner's first review showed the default
  slide 1. The drive itself always stands at a gate before it resumes, so it
  asks for the succeeded cover there first. The autopilot's generation and
  slide 1's cover fields at scheduling are read from the database, so a
  restart loses nothing. The cover is stored with the same rules and the
  same write as the background selection (consent, the generation belongs
  to this carousel, the owner's choice wins, the lock-version
  compare-and-set), before the finalize render, so the first final review
  already shows it. Nothing is re-rendered or published by the selection.

  Scenario: A drive straight through to the final review shows the cover
    Given the autopilot's cover generation succeeded while research ran
    And the drive approves every gate without a pause the selection can see
    When the drive reaches the final review
    Then slide_cover is the generated asset with kind ai_image
    And the background selection's own skip changed nothing

  Scenario: A restart before the next gate still shows the cover
    Given the autopilot's cover generation succeeded
    And a deploy restarted the worker before the next gate
    When the resumed drive stands at a gate
    Then slide_cover is the generated asset with kind ai_image
    And it is stored before the first final review

  Scenario: An owner's pick made after scheduling is kept across a restart
    Given the autopilot's cover generation succeeded
    And a deploy restarted the worker
    And the owner bound another slide-1 photo after the job was scheduled
    When the resumed drive stands at a gate
    Then slide 1 keeps the owner's photo and the skip reason is manual_choice

  Scenario: The drive stores the cover at a gate before it resumes
    Given a succeeded autopilot cover waits for slide 1
    When the drive stands at a gate
    Then the cover is stored and the gate is read again before any resume
    And the next gate finds it already in place and resumes

  Scenario: The owner's photo chosen before the gate is kept
    Given the owner bound another slide-1 photo after the job was scheduled
    When the drive stands at a gate
    Then slide 1 keeps the owner's photo and the skip reason is manual_choice

  Scenario: A cover the owner chose before the job is kept
    Given the carousel was created with the owner's GrokBot cover
    When the drive stands at a gate
    Then slide_cover is unchanged and the skip reason is owner_cover

  Scenario: Without consent the drive stores nothing
    Given the owner's cover consent is off
    When the drive stands at a gate
    Then nothing is read or written and the drive resumes as before

  Scenario: A failed generation leaves slide 1 alone
    Given the autopilot's cover generation failed
    When the drive stands at a gate
    Then slide_cover is unchanged and the drive resumes as before

  Scenario: A conflict at the gate is tried again at the next gate
    Given another writer holds the project lock at a gate
    When the drive stands at that gate
    Then nothing is written and the drive resumes
    And the cover is stored at the next gate

  Scenario: A crash while storing the cover never breaks the drive
    Given the cover store raises at a gate
    When the drive stands at that gate
    Then the crash is logged and the drive resumes as before
