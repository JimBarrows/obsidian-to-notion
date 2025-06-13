Feature: Notion API Client
  As a migration tool
  I need to interact with the Notion API
  So that I can create and update pages with proper rate limiting

  Background:
    Given I have a valid Notion API token
    And I have a target database ID

  Scenario: Create a new page in Notion
    Given I have a NotionMigrationClient instance
    When I create a page with title "Test Page" and content "Test content"
    Then the page should be created successfully
    And the page should have the correct title and content

  Scenario: Rate limiting prevents exceeding API limits
    Given I have a NotionMigrationClient with rate limit of 2 requests per second
    When I make 5 consecutive API requests
    Then the requests should be rate limited
    And no more than 2 requests should occur within any 1 second window

  Scenario: Automatic retry on API errors
    Given I have a NotionMigrationClient instance
    And the API will fail with a transient error on first attempt
    When I create a page
    Then the request should be retried
    And the page should be created on retry

  Scenario: Handle rate limit errors from Notion API
    Given I have a NotionMigrationClient instance
    And the API will return a rate limit error with retry-after header
    When I create a page
    Then the client should wait for the specified retry-after period
    And the page should be created after waiting

  Scenario: Query database for existing pages
    Given I have a NotionMigrationClient instance
    And the database contains 3 existing pages
    When I query the database
    Then I should receive all 3 pages
    And pagination should be handled automatically

  Scenario: Update existing page properties
    Given I have a NotionMigrationClient instance
    And a page exists with ID "test-page-id"
    When I update the page title to "Updated Title"
    Then the page should be updated successfully
    And the new title should be "Updated Title"

  Scenario: Deduplication prevents duplicate pages
    Given I have a DeduplicationManager instance
    And the database contains a page titled "Existing Page"
    When I check if "Existing Page" should be skipped
    Then the deduplication check should return true
    And I should get the existing page ID

  Scenario: Deduplication handles case-insensitive titles
    Given I have a DeduplicationManager instance
    And the database contains a page titled "Test Page"
    When I check if "test page" should be skipped
    Then the deduplication check should return true

  Scenario: Upload file attachment (not implemented)
    Given I have a NotionMigrationClient instance
    And I have a test file "test.png"
    When I upload the file
    Then the file upload should return None
    And a warning should be logged about external storage
