Feature: Obsidian Vault Processing
  As a user migrating from Obsidian to Notion
  I want to parse my Obsidian vault
  So that I can extract all content and metadata for migration

  Background:
    Given I have an Obsidian vault at "test_vault"

  Scenario: Process empty vault
    Given the vault is empty
    When I process the vault
    Then I should find 0 markdown files
    And I should find 0 attachments
    And the wikilink map should be empty

  Scenario: Process vault with markdown files
    Given the vault contains the following markdown files:
      | filename          | title                    | content                          |
      | Welcome.md        | Welcome to My Vault      | This is a test vault             |
      | Getting Started.md| Getting Started          | Learn how to use Obsidian        |
      | Projects/Alpha.md | Project Alpha            | Important project documentation   |
    When I process the vault
    Then I should find 3 markdown files
    And each file should have its content and metadata extracted

  Scenario: Extract frontmatter metadata
    Given a markdown file "test.md" with frontmatter:
      """
      ---
      title: Test Document
      tags: [test, documentation]
      date: 2024-01-15
      custom_field: value
      ---

      # Content
      This is the content.
      """
    When I process the vault
    Then the file metadata should contain:
      | field        | value                    |
      | title        | Test Document            |
      | tags         | [test, documentation]    |
      | date         | 2024-01-15              |
      | custom_field | value                    |

  Scenario: Extract various wikilink formats
    Given a markdown file with content:
      """
      - Basic link: [[Note Name]]
      - Link with alias: [[Original Note|Display Name]]
      - Link to section: [[Note#Section]]
      - Link with section and alias: [[Note#Section|Custom Text]]
      - Embedded note: ![[Embedded Note]]
      - Embedded image: ![[image.png]]
      """
    When I process the vault
    Then I should find the following wikilinks:
      | original                        | note_name      | heading  | display_text   | is_embed |
      | [[Note Name]]                   | Note Name      |          | Note Name      | false    |
      | [[Original Note\|Display Name]] | Original Note  |          | Display Name   | false    |
      | [[Note#Section]]                | Note           | Section  | Note           | false    |
      | [[Note#Section\|Custom Text]]   | Note           | Section  | Custom Text    | false    |
      | ![[Embedded Note]]              | Embedded Note  |          | Embedded Note  | true     |
      | ![[image.png]]                  | image.png      |          | image.png      | true     |

  Scenario: Build wikilink map for cross-references
    Given the vault contains files:
      | filename       | title          |
      | Welcome.md     | Welcome        |
      | Index.md       | Index          |
      | ideas/AI.md    | AI Research    |
    When I process the vault
    Then the wikilink map should contain:
      | title        | path           |
      | welcome      | Welcome.md     |
      | index        | Index.md       |
      | ai research  | ideas/AI.md    |

  Scenario: Detect embedded attachments
    Given a markdown file with content:
      """
      # Document with attachments

      ![[presentation.pdf]]
      ![[diagram.png]]
      ![[spreadsheet.xlsx]]
      ![[photo.jpg]]

      Regular link: [[Not an attachment]]
      """
    When I process the vault
    Then I should find 4 embedded attachments:
      | filename           |
      | presentation.pdf   |
      | diagram.png        |
      | spreadsheet.xlsx   |
      | photo.jpg          |

  Scenario: Sanitize text for Notion compatibility
    Given I need to sanitize the following text:
      | original                            | sanitized                    |
      | My File/Name*With<Special>Chars?   | My File-NameWithSpecialChars |
      | Note: Important\|Details            | Note- Important-Details      |
      | Path\\To\\File                      | Path--To--File               |
      | Text with   spaces                  | Text with   spaces           |
    When I sanitize each text
    Then the sanitized versions should match the expected results

  Scenario: Handle file processing errors gracefully
    Given a markdown file that cannot be read
    When I process the vault
    Then the file should be skipped
    And an error should be logged
    And processing should continue with other files

  Scenario: Process files with invalid YAML frontmatter
    Given the vault contains files with invalid YAML:
      | filename | content |
      | template.md | ---\nauthor: {{author}}\ndate: {{date}}\n---\n# Template |
      | tabs.md | ---\nauthor:\n\t- [[Robert Turnbull]]\n---\n# Tab Issue |
      | missing_colon.md | ---\nbusiness name:Copart\n---\n# Missing Space |
      | markdown_in_yaml.md | ---\nauthor: [Kendra Cherry](https://example.com)\n---\n# Link Issue |
    When I process the vault
    Then I should find 4 markdown files
    And each file should be processed despite YAML errors
    And invalid frontmatter should be skipped or corrected

  Scenario: Handle template placeholders in frontmatter
    Given a markdown file with template placeholders:
      """
      ---
      author: {{author}}
      title: {{title}}
      date: {{date}}
      tags: [{{tag1}}, {{tag2}}]
      ---

      # Document with Templates
      This document contains template placeholders.
      """
    When I process the vault
    Then the file should be processed successfully
    And template placeholders should be handled gracefully
    And the content should be preserved

  Scenario: Fix common YAML syntax errors
    Given the vault contains files with fixable YAML errors:
      | filename | original_yaml | expected_fix |
      | tabs_to_spaces.md | "author:\n\t- Name" | "author:\n  - Name" |
      | missing_space.md | "key:value" | "key: value" |
      | quotes_needed.md | "title: Book: Subtitle" | "title: 'Book: Subtitle'" |
    When I process the vault with error recovery
    Then each file should have corrected YAML frontmatter
    And the files should be processed successfully

  Scenario: Continue processing when YAML parsing fails
    Given a vault with multiple files including invalid YAML
    When I process the vault
    Then all valid files should be processed
    And files with invalid YAML should not stop the migration
    And appropriate warnings should be logged for invalid files
