Feature: The generation worker releases the page cache of the carousel files it writes
  Every run writes the slide JPGs, the HD slides, the PDFs and the artifact copies
  (about 120 to 220 MB) and never reads them again: the backend serves them. Linux
  charges the page cache of those writes to the worker's cgroup, so its memory rose
  after every run and filled the 1600 MiB cap. Once the files are on disk the worker
  drops their cached pages, so its memory between runs stays at the process baseline.

  Scenario: Releasing a directory drops the cache of every file under it
    Given a carousel output directory with files in nested folders
    When its page cache is released
    Then every file is flushed to disk and its cached pages are dropped
    And the number of released files is returned

  Scenario: A file that cannot be released does not stop the others
    Given an output directory where one file cannot be opened
    When its page cache is released
    Then the other files are still released

  Scenario: Releasing is a no-op where the platform has no fadvise
    Given a platform without posix_fadvise
    When the page cache of an output directory is released
    Then nothing is touched and zero files are reported

  Scenario: A slide export releases the slides it wrote
    Given a carousel exported to slide images
    When the export finishes
    Then the page cache of the export directory is released

  Scenario: A promoted artifact releases the whole carousel output
    Given a carousel whose artifact version is built and activated
    When the activation commits
    Then the page cache of the carousel output directory is released
