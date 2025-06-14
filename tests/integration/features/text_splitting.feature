Feature: Text splitting for Notion's character limits
  As a user migrating long documents from Obsidian to Notion
  I want long paragraphs to be split to respect Notion's 2000 character limit
  So that my content is properly imported without API errors

  Background:
    Given I have an Obsidian vault at "test_vault"
    And I have a Notion database with ID "test-database-id"

  Scenario: Short paragraph under limit
    Given I have a markdown file "notes/short.md" with content:
      """
      ---
      title: Short Note
      ---
      # Short Note

      This is a short paragraph that is well under the 2000 character limit.
      It should be imported as a single paragraph block in Notion.
      """
    When I migrate the vault to Notion
    Then the Notion page should have 1 paragraph block
    And the paragraph should contain "This is a short paragraph"

  Scenario: Single paragraph exceeding 2000 characters
    Given I have a markdown file "notes/long.md" with content:
      """
      ---
      title: Long Note
      ---
      # Long Note

      <LONG_TEXT_2500_CHARS>
      """
    When I migrate the vault to Notion
    Then the Notion page should have 2 paragraph blocks
    And each paragraph block should be under 2000 characters
    And the combined text should equal the original content

  Scenario: Multiple paragraphs with one exceeding limit
    Given I have a markdown file "notes/mixed.md" with content:
      """
      ---
      title: Mixed Length Note
      ---
      # Mixed Length Note

      This is a short first paragraph.

      <LONG_TEXT_2500_CHARS>

      This is another short paragraph at the end.
      """
    When I migrate the vault to Notion
    Then the Notion page should have 4 paragraph blocks
    And paragraph 1 should contain "This is a short first paragraph"
    And paragraphs 2 and 3 should contain the split long text
    And paragraph 4 should contain "This is another short paragraph at the end"

  Scenario: Very long paragraph requiring multiple splits
    Given I have a markdown file "notes/very_long.md" with content:
      """
      ---
      title: Very Long Note
      ---
      # Very Long Note

      <LONG_TEXT_5000_CHARS>
      """
    When I migrate the vault to Notion
    Then the Notion page should have 3 paragraph blocks
    And each paragraph block should be under 2000 characters
    And no paragraph should be cut mid-word

  Scenario: Paragraph with exactly 2000 characters
    Given I have a markdown file "notes/exact.md" with content:
      """
      ---
      title: Exact Length Note
      ---
      # Exact Length Note

      <TEXT_EXACTLY_2000_CHARS>
      """
    When I migrate the vault to Notion
    Then the Notion page should have 1 paragraph block
    And the paragraph should be exactly 2000 characters

  Scenario: Multi-line paragraph exceeding limit
    Given I have a markdown file "notes/multiline.md" with content:
      """
      ---
      title: Multi-line Note
      ---
      # Multi-line Note

      Line 1: This is the first line of a multi-line paragraph.
      Line 2: This line contains additional content.
      Line 3: And this pattern continues for many lines.
      <CONTINUE_TO_2500_CHARS_TOTAL>
      """
    When I migrate the vault to Notion
    Then the Notion page should have 2 paragraph blocks
    And line breaks within chunks should be preserved
    And no line should be split across chunks

  Scenario: Empty lines between paragraphs
    Given I have a markdown file "notes/spaced.md" with content:
      """
      ---
      title: Spaced Note
      ---
      # Spaced Note

      First paragraph here.


      Second paragraph after multiple empty lines.

      <LONG_TEXT_2200_CHARS>

      Final paragraph.
      """
    When I migrate the vault to Notion
    Then the Notion page should have 4 paragraph blocks
    And empty lines should not create empty paragraph blocks
    And the long text should be properly split

  Scenario: Text with special characters
    Given I have a markdown file "notes/special.md" with content:
      """
      ---
      title: Special Characters Note
      ---
      # Special Characters

      This paragraph contains special characters like émojis 🎉, symbols ™®©, and various quotes "''""‚.
      <CONTINUE_WITH_SPECIAL_CHARS_TO_2100_CHARS>
      """
    When I migrate the vault to Notion
    Then the Notion page should have 2 paragraph blocks
    And special characters should be preserved in both blocks
    And character count should properly account for multi-byte characters
