Feature: Reliable pre-commit hooks (AE-0168)
  A normal `git commit` runs the husky hooks (prettier/eslint via lint-staged,
  and commitlint) reliably from the repo root and inside a git worktree, so
  unformatted code and non-conventional messages cannot land — eliminating the
  recurring "format gate fails late because someone used --no-verify" class.

  Background:
    Given core.hooksPath is the relative ".husky" (set by the frontend prepare step)
    And the hooks cd into frontend and unset the git worktree env vars

  Scenario: A staged unformatted frontend file is auto-fixed on commit
    Given a staged frontend ".ts" file with formatting issues
    When the user runs "git commit" without --no-verify
    Then lint-staged runs the frontend eslint/prettier and formats the file
    And the commit succeeds with the formatted content

  Scenario: A non-conventional commit message is rejected
    Given a staged change
    When the user commits with a non-conventional message
    Then commitlint rejects it (type/subject errors) and the commit is blocked

  Scenario: The hook works inside a git worktree
    Given the commit runs inside a linked git worktree
    When the pre-commit hook runs
    Then GIT_DIR/GIT_WORK_TREE are unset so lint-staged resolves the frontend cwd
    And eslint/prettier are found in frontend/node_modules (no ENOENT)
