Feature: Carousel generation runs in a capped PgQueuer worker
  Carousel generation leaves the web process: approvals and dashboard resumes
  record a generation run, a dispatcher hands it to PgQueuer, and a separate,
  resource-capped worker drives it one carousel at a time. The worker goes live
  when it merges (Pedro: no feature flag).

  Scenario: Several approved themes are generated one after another
    Given three autopilot runs were queued within one minute
    When the worker processes the queue with a concurrency of 1
    Then only one job runs at a time and they start in FIFO order

  Scenario: One autopilot drive steps a run until the owner has to act
    Given an autopilot run that keeps advancing phase by phase
    When its drive job runs
    Then it steps the run until the run waits for the owner, then ends

  Scenario: A drive with nothing to do comes back later
    Given an autopilot run whose gate is still in flight
    When its drive job steps it and nothing happens
    Then the job is retried later with the same position in the queue

  Scenario: A run interrupted by a deploy resumes by itself
    Given a project left in progress by a worker that died mid-phase
    When the drive job for its run is picked again
    Then the orphaned phase is reaped and the parked node runs again
    And the run is not escalated as run_stale

  Scenario: A queued dashboard resume owns its in-progress project
    Given a dashboard resume is queued for a project marked in progress
    When an autopilot drive for the same project starts
    Then the drive waits instead of reaping the project

  Scenario: A re-picked dashboard resume does not re-apply the review decision
    Given a dashboard resume whose first attempt died after it started
    When the job is picked again
    Then the orphaned phase is reaped and the parked node runs again
    And the review decision is not sent a second time

  Scenario: A dashboard resume a deploy killed before the cutover resumes in the worker
    Given a carousel project left in progress with no queued run and no autopilot run
    And another project whose drive lock is held, and one that belongs to an autopilot run
    When the deploy one-shot applies the queue schema
    Then one recovery is queued for the orphaned project only, and a second run queues none
    And the worker reaps it and runs the parked node again without a review decision

  Scenario: A transient failure retries with backoff and jitter
    Given a job fails with a provider timeout
    When the handler records the failure
    Then the run waits for a retry 30 s to 30 min later with 20 % jitter

  Scenario: A permanent failure parks the run with its reason
    Given a job fails with an error no retry can fix
    When the handler records the failure
    Then the run is a dead letter with a classified reason
    And one owner notice is staged

  Scenario: A phase that keeps failing is parked once its budget is spent
    Given a phase was started three times without finishing
    When the job starts it a fourth time
    Then the run is a dead letter with the phase budget reason, before any work runs

  Scenario: A run that keeps advancing is never taken for poison
    Given a run whose phases each finish cleanly
    When it goes through more phases than the run budget
    Then it is never dead-lettered

  Scenario: A dead-lettered run is requeued once
    Given a dead-lettered run
    When it is requeued
    Then it is queued again with the failing phase's attempts reset
    And a second requeue changes nothing

  Scenario: The same confirmation twice queues one run
    Given a resume or an autopilot run was already staged
    When the same stage arrives again
    Then exactly one active generation run exists

  Scenario: The dispatcher stages and hands over the queued work
    Given an active autopilot run without a generation run and a queued run without a job
    When the dispatcher runs
    Then the missing run is staged and every queued run gets exactly one PgQueuer job

  Scenario: A held job the handler did not mirror becomes a dead letter
    Given PgQueuer holds a failed job whose generation run is still active
    When the dispatcher runs
    Then the run is a dead letter, one owner notice is staged and the held job is dropped

  Scenario: A lost job is handed over again
    Given an active generation run whose PgQueuer job no longer exists
    When the dispatcher runs
    Then the run is queued again without a job

  Scenario: Two drivers claim the same project and exactly one drives
    Given two drivers try to take the same project's drive lock at once
    Then exactly one of them drives and the other is told the lock is busy

  Scenario: Losing the lock connection stops the drive
    Given a drive holds the project's drive lock
    When the lock connection dies
    Then the drive is stopped with a lock-lost error

  Scenario: The dashboard resume is queued, not run in the web process
    Given an editor approves a gate in the dashboard
    When the resume route answers 202
    Then a workflow resume run is queued in the same transaction and no phase runs in the web process

  Scenario: The dashboard start is refused while the worker drives the project
    Given the worker holds a project's drive lock
    When the dashboard start runs for that project
    Then it answers 409 mutation_in_progress

  Scenario: The worker stops at the next phase boundary on shutdown
    Given the worker received SIGTERM during a drive
    When the current phase ends
    Then the drive yields and its job is picked again at once by the next worker

  Scenario: The worker refuses to start without the Postgres checkpointer
    Given the checkpointer is memory or SQLite
    When the worker starts
    Then it refuses with a configuration error

  Scenario: Progress events reach the web through NOTIFY
    Given the worker publishes a workflow event
    When the web relay receives it
    Then the web's SSE subscribers get the same event and the run stage is mirrored

  Scenario: An oversized review event is rebuilt from the checkpoint
    Given a review_required event larger than a NOTIFY payload
    When it is relayed
    Then it travels without its gate and the web rebuilds the gate from the checkpoint

  Scenario: Queue health is reported and alerts fire once per episode
    Given the worker has been gone for 10 minutes or the oldest queued run waits over 6 hours
    When the queue monitor reads the numbers
    Then Pedro gets one alert per episode and readiness reports the queue numbers

  Scenario: The queue schema reaches prod with the deploy
    Given a Postgres database without generation_runs or PgQueuer's tables
    When the one-shot runs with --apply --verify
    Then generation_runs, its indexes and PgQueuer's tables exist and it exits 0

  Scenario: A second queue schema run changes nothing
    Given the queue schema is already in place
    When the one-shot runs with --apply again
    Then nothing is created and PgQueuer applies no statement

  Scenario: Verify fails while a queue object is missing
    Given PgQueuer's tables are missing
    When the one-shot runs with --verify only
    Then it exits 1 and names what is missing

  Scenario: The queue schema one-shot is a no-op outside Postgres
    Given a SQLite database
    When the one-shot runs with --apply --verify
    Then it reports there is nothing to do and exits 0

  Scenario: The queue schema command needs a mode
    When the one-shot runs without --apply or --verify
    Then it exits 2 with a usage error

  Scenario: The deploy installs the queue schema and drains the worker
    Given the deploy workflow
    Then the queue one-shot runs before the stack comes up and its failure fails the job at the end
    And the worker is stopped with a 300 s grace before the stack goes down

  Scenario: The worker container is capped and hardened
    Given the production compose file
    Then the generation worker runs the same image with pgq run, a 1600 MiB memory cap without swap, low CPU shares, a read-only root, no capabilities and its own healthcheck

  Scenario: PgQueuer keeps a held job apart from a new job with the same dedupe key
    Given a job with a dedupe key is held as failed
    When a new job with the same key is enqueued and the held one is requeued
    Then the new job is accepted, and the requeue is refused while the new one is active

  Scenario: PgQueuer delays a job until its execute_after
    Given a job enqueued with a delay
    Then it is not dequeued before the delay passes and is dequeued after

  Scenario: PgQueuer re-picks a job after the configured heartbeat timeout without counting an attempt
    Given a picked job whose heartbeat is older than the timeout
    When another worker dequeues
    Then it gets the job and the job's attempts are unchanged

  Scenario: PgQueuer dequeues in FIFO order under a concurrency limit of 1
    Given three jobs queued one after another
    When workers dequeue with a concurrency limit of 1
    Then only one job is picked at a time, in the order they were queued

  Scenario: PgQueuer requeues a held job
    Given a job held as failed
    When it is requeued
    Then it is queued again with its attempts reset

  Scenario: PgQueuer fires a schedule once across workers
    Given two schedulers register the same cron schedule
    When the schedule is due
    Then only one of them claims it

  Scenario: PgQueuer log rows can be purged by age
    Given old and recent rows in PgQueuer's log
    When rows older than the retention are deleted
    Then only the recent rows remain

  Scenario: The validation droplet never holds production credentials
    Given the droplet environment built by the validation script
    Then every outbound credential is a stub and the build fails when a production value is present

  Scenario: The production validation refuses unsafe moments
    Given the production validation of the queue with one QA carousel
    When it is started between 11:05 and 13:30 UTC, during a deploy, or with another generation run or QA project active
    Then it refuses to start, and its driver only ever changes the project whose topic carries the QA marker

  Scenario: The production validation stops on the first danger sign
    Given the QA carousel is running under a gentle public-page load
    When the health route fails twice in a row, the rolling p95 exceeds 3x the idle baseline, a container is OOM-killed or under 300 MiB is available
    Then the run stops, and the QA carousel and its rows are deleted

  Scenario: The production validation kills and restarts the worker once each
    Given a worker job of the QA carousel is running and no other generation run is active
    When the chaos steps are due
    Then the worker is killed during one QA job and gracefully restarted during a later one, never while another run is active

  Scenario: A revert of the worker hands the queued work back
    Given a dashboard resume is queued and its project is in progress with no run heartbeat
    When the rollback one-shot runs before the revert
    Then the project is back at its gate and every active generation run is cancelled

  Scenario: A re-run image waits for the job its dead driver started
    Given the image phase died while a Grok Bot job for a slide was still pending
    When the phase runs again for the same slide and prompt
    Then it waits for that job instead of sending the webhook again
