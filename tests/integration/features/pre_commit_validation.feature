Feature: Pre-commit Validation
  As a developer working on the project
  I want automated validation before each commit
  So that code quality issues are caught early

  Background:
    Given I have a working Git repository
    And pre-commit is installed

  Scenario: Pre-commit hooks run on commit attempt
    Given I have modified Python files
    When I attempt to commit the changes
    Then pre-commit hooks should run automatically
    And each configured hook should execute in order

  Scenario: Black formatting check
    Given I have Python files with incorrect formatting
    When pre-commit runs the Black hook
    Then Black should automatically format the files
    And the commit should include the formatted changes

  Scenario: isort import sorting
    Given I have Python files with unsorted imports
    When pre-commit runs the isort hook
    Then imports should be automatically sorted
    And the changes should be staged for commit

  Scenario: Flake8 linting
    Given I have Python files with linting errors
    When pre-commit runs the Flake8 hook
    Then linting errors should be reported
    And the commit should be blocked if errors exist

  Scenario: Mypy type checking
    Given I have Python files with type errors
    When pre-commit runs the Mypy hook
    Then type errors should be reported
    And the commit should be blocked if type errors exist

  Scenario: Ruff linting and formatting
    Given I have Python files with style issues
    When pre-commit runs the Ruff hook
    Then Ruff should check and optionally fix issues
    And the commit should reflect any automatic fixes

  Scenario: All hooks pass successfully
    Given I have clean Python files that pass all checks
    When I attempt to commit
    Then all pre-commit hooks should pass
    And the commit should proceed successfully

  Scenario: Pre-commit prevents commits with failures
    Given I have files that fail validation
    When I attempt to commit
    Then pre-commit should block the commit
    And display clear error messages for each failure

  Scenario: Skip pre-commit with --no-verify
    Given I have files that would fail validation
    When I commit with the --no-verify flag
    Then pre-commit hooks should be skipped
    And the commit should proceed without validation

  Scenario: Pre-commit configuration is valid
    Given the .pre-commit-config.yaml file exists
    When I validate the pre-commit configuration
    Then the configuration should be valid
    And all referenced hooks should be properly defined
