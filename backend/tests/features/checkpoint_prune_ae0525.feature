Feature: Old carousel checkpoints are pruned safely, with Pedro's sign-off
  The LangGraph checkpoint tables keep every step of every carousel forever. The old
  cleanup job never matched a thread (it looked for a carousel- prefix the workflow
  never writes). Pruning is irreversible, so it runs as a dry run first, deletes only
  the threads Pedro signed off, keeps a backup, and keeps each thread's latest
  checkpoint so a pruned carousel still opens.

  Scenario: A dry run lists the matched threads and deletes nothing
    Given a rejected carousel and a published carousel last updated before the TTL, each with checkpoint history
    When the prune runs without --apply
    Then it lists both threads with their project states and the rows each table would lose
    And every checkpoint row is still there

  Scenario: Only finished rejected or published carousels past the TTL are matched
    Given carousels that are recent, still running, waiting for a republish, approved but unpublished, or not a carousel thread
    When the prune runs without --apply
    Then none of them is listed

  Scenario: The prune deletes only the signed-off threads and keeps a backup
    Given two matched threads and a sign-off file naming one of them
    When the prune runs with --apply and a backup file
    Then only the signed-off thread loses its old checkpoints, writes and blobs
    And the backup file holds every deleted row
    And the deleted counts per table are reported

  Scenario: A pruned thread keeps its workflow state
    Given a thread parked at a human gate after several steps
    When it is pruned
    Then its state values, next node and pending interrupt are the same as before

  Scenario: A signed-off thread that is no longer eligible stops the prune
    Given a sign-off file naming a thread whose carousel was resumed after the dry run
    When the prune runs with --apply
    Then it refuses and deletes nothing

  Scenario: A prune that deletes nothing is reported as a failure
    Given a signed-off thread with old checkpoint rows
    And the delete removes no row
    When the prune runs with --apply
    Then it exits non-zero with an explicit error

  Scenario: Apply without a sign-off file or a backup file is a usage error
    When the prune runs with --apply but without --threads or --backup
    Then it exits with the usage error code and touches nothing

  Scenario: The workflow engine and the prune agree on the thread id
    Given a carousel project id
    Then the workflow engine's checkpoint thread id and the prune's are the same value
