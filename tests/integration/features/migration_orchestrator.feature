Feature: Obsidian to Notion Migration Orchestrator
  As a user
  I want to migrate my Obsidian vault to Notion
  So that I can use my notes in Notion with proper formatting and links

  Background:
    Given I have a valid configuration
    And I have a test Obsidian vault

  Scenario: Successful migration of simple vault
    Given the vault contains the following files
      | filename     | title        | content                   |
      | Welcome.md   | Welcome      | This is my welcome note   |
      | Projects.md  | Projects     | My ongoing [[Welcome]]    |
    And I have a Notion database ID
    When I run the migration
    Then 2 pages should be created in Notion
    And the migration should complete successfully
    And the report should show 2 successful migrations

  Scenario: Dry run migration
    Given the vault contains the following files
      | filename     | title        | content                   |
      | Note1.md     | Note 1       | First note                |
      | Note2.md     | Note 2       | Second note               |
    When I run the migration in dry-run mode
    Then no pages should be created in Notion
    And the output should show what would be migrated
    And the report should show 2 would-be migrations

  Scenario: Migration with duplicate detection
    Given the vault contains the following files
      | filename     | title        | content                   |
      | Existing.md  | Existing     | This already exists       |
      | New.md       | New Note     | This is new               |
    And the Notion database already contains a page titled "Existing"
    When I run the migration with skip duplicates enabled
    Then 1 page should be created in Notion
    And 1 page should be skipped
    And the report should show 1 successful and 1 skipped

  Scenario: Migration with wikilink conversion
    Given the vault contains the following files
      | filename     | title        | content                           |
      | Page1.md     | Page 1       | Link to [[Page 2]]                |
      | Page2.md     | Page 2       | Link back to [[Page 1\|First Page]] |
    When I run the migration
    Then 2 pages should be created in Notion
    And wikilinks should be converted to Notion page mentions
    And the report should show successful link resolution

  Scenario: Handle migration errors gracefully
    Given the vault contains the following files
      | filename     | title        | content                   |
      | Good.md      | Good Note    | This will succeed         |
      | Bad.md       | Bad Note     | This will fail            |
    And the Notion API will fail for "Bad Note"
    When I run the migration
    Then 1 page should be created successfully
    And 1 page should fail to migrate
    And the report should include error details

  Scenario: Empty vault migration
    Given the vault is empty
    When I run the migration
    Then no pages should be created
    And the migration should complete with "no_files" status
    And the report should indicate no files found

  Scenario: Migration with metadata preservation
    Given a markdown file with frontmatter
      """
      ---
      title: Test Document
      tags: [important, project]
      date: 2024-01-15
      custom_field: custom_value
      ---

      # Content
      This is the content with [[links]].
      """
    When I run the migration
    Then the Notion page should have the title "Test Document"
    And the page properties should include the metadata fields
    And the content should be properly formatted

  Scenario: Progress tracking during migration
    Given the vault contains 5 markdown files
    When I run the migration with progress tracking
    Then progress updates should be displayed
    And the final statistics should show the results
    And the progress bar should complete at 100%
