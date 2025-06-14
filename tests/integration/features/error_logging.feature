Feature: Enhanced Error Logging
  As a developer using the migration tool
  I want comprehensive error logging with full context
  So that I can effectively debug issues when migrations fail

  Background:
    Given I have a working migration environment
    And error logging is configured

  Scenario: Log error with file context during parsing
    Given I have an Obsidian file with invalid content
    When the parser encounters an error processing the file
    Then the error log should contain the file path
    And the error log should contain the error message
    And the error log should contain the parsing phase context
    And the error log should contain a stack trace

  Scenario: Log error with context during wikilink conversion
    Given I have an Obsidian file with malformed wikilinks
    When the wikilink converter encounters an error
    Then the error log should contain the source file path
    And the error log should contain the specific wikilink that failed
    And the error log should contain the line number
    And the error log should contain transformation phase context

  Scenario: Log error with API context during Notion upload
    Given I have a valid Obsidian file
    When the Notion API returns an error during upload
    Then the error log should contain the file being uploaded
    And the error log should contain the API error details
    And the error log should contain the retry attempt number
    And the error log should contain the upload phase context

  Scenario: Log error with full migration context
    Given I have multiple Obsidian files
    When an error occurs during batch processing
    Then the error log should contain the current file being processed
    And the error log should contain the batch number and size
    And the error log should contain files processed successfully before error
    And the error log should contain memory usage information

  Scenario: Log configuration errors with context
    Given I have an invalid configuration
    When the configuration is loaded
    Then the error log should contain the configuration file path
    And the error log should contain the specific configuration error
    And the error log should contain the configuration section that failed
    And the error log should contain suggested fixes

  Scenario: Log errors to configured file
    Given I have configured a custom log file path
    When any error occurs during migration
    Then the error should be written to the configured log file
    And the log entry should have proper timestamp formatting
    And the log entry should have appropriate severity level
    And the log entry should be structured for easy parsing

  Scenario: Preserve error context through decorators
    Given I have a file operation that fails
    When the error passes through the safe_file_operation decorator
    Then the original error context should be preserved
    And additional decorator context should be added
    And the full call stack should be maintained
    And all relevant file metadata should be logged
