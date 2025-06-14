Feature: Obsidian metadata mapping to Notion properties
  As a user migrating from Obsidian to Notion
  I want my Obsidian metadata to be properly mapped to Notion properties
  So that my content organization is preserved in Notion

  Background:
    Given I have an Obsidian vault at "test_vault"
    And I have a Notion database with ID "test-database-id"
    And the Notion database has the following properties:
      | property_name | property_type |
      | Name          | title         |
      | Tags          | multi_select  |
      | Directory     | rich_text     |
      | URL           | url           |
      | Type          | rich_text     |
      | Modified      | date          |

  Scenario: Map tags from list format
    Given I have a markdown file "notes/test.md" with content:
      """
      ---
      title: Test Note
      tags: [python, testing, automation]
      ---
      # Test Note
      This is a test note.
      """
    When I migrate the vault to Notion
    Then the Notion page should have property "Tags" with values:
      | value      |
      | python     |
      | testing    |
      | automation |

  Scenario: Map tags from string format
    Given I have a markdown file "notes/test.md" with content:
      """
      ---
      title: Test Note
      tags: python, testing, automation
      ---
      # Test Note
      This is a test note.
      """
    When I migrate the vault to Notion
    Then the Notion page should have property "Tags" with values:
      | value      |
      | python     |
      | testing    |
      | automation |

  Scenario: Map single tag
    Given I have a markdown file "notes/test.md" with content:
      """
      ---
      title: Test Note
      tags: python
      ---
      # Test Note
      This is a test note.
      """
    When I migrate the vault to Notion
    Then the Notion page should have property "Tags" with values:
      | value  |
      | python |

  Scenario: Map directory from file path
    Given I have a markdown file "projects/web/frontend/index.md" with content:
      """
      ---
      title: Frontend Index
      ---
      # Frontend Documentation
      """
    When I migrate the vault to Notion
    Then the Notion page should have property "Directory" with value "projects/web/frontend"

  Scenario: Map URL metadata
    Given I have a markdown file "bookmarks/article.md" with content:
      """
      ---
      title: Interesting Article
      url: https://example.com/article
      ---
      # Article Notes
      """
    When I migrate the vault to Notion
    Then the Notion page should have property "URL" with value "https://example.com/article"

  Scenario: Map type metadata
    Given I have a markdown file "notes/meeting.md" with content:
      """
      ---
      title: Team Meeting
      type: meeting-notes
      ---
      # Meeting Notes
      """
    When I migrate the vault to Notion
    Then the Notion page should have property "Type" with value "meeting-notes"

  Scenario: Map modified date
    Given I have a markdown file "notes/test.md" with content:
      """
      ---
      title: Test Note
      modified: 2024-01-15T10:30:00Z
      ---
      # Test Note
      """
    When I migrate the vault to Notion
    Then the Notion page should have property "Modified" with date "2024-01-15T10:30:00Z"

  Scenario: Fall back to date field when modified is not present
    Given I have a markdown file "notes/test.md" with content:
      """
      ---
      title: Test Note
      date: 2024-01-10T08:00:00Z
      ---
      # Test Note
      """
    When I migrate the vault to Notion
    Then the Notion page should have property "Modified" with date "2024-01-10T08:00:00Z"

  Scenario: Handle all metadata fields together
    Given I have a markdown file "projects/python/app.md" with content:
      """
      ---
      title: Python App Documentation
      tags: [python, backend, api]
      url: https://github.com/user/project
      type: documentation
      modified: 2024-01-20T14:00:00Z
      ---
      # Python Application
      """
    When I migrate the vault to Notion
    Then the Notion page should have property "Tags" with values:
      | value   |
      | python  |
      | backend |
      | api     |
    And the Notion page should have property "Directory" with value "projects/python"
    And the Notion page should have property "URL" with value "https://github.com/user/project"
    And the Notion page should have property "Type" with value "documentation"
    And the Notion page should have property "Modified" with date "2024-01-20T14:00:00Z"
