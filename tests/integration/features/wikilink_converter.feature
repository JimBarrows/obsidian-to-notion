Feature: Wikilink Converter
  As a user migrating from Obsidian to Notion
  I want my wikilinks to be converted to Notion page mentions
  So that my document relationships are preserved

  Scenario: Convert basic wikilinks
    Given I have a WikilinkConverter instance
    When I add pages to the cache
      | title      | page_id    |
      | Test Page  | page-123   |
      | Notes      | page-456   |
    And I convert content with wikilinks
      | content                               | wikilinks                           |
      | Check out [[Test Page]] for details   | [{"note_name": "Test Page"}]        |
    Then the content should contain Notion links
    And no broken links should be reported

  Scenario: Convert wikilinks with aliases
    Given I have a WikilinkConverter instance
    When I add pages to the cache
      | title      | page_id    |
      | Test Page  | page-123   |
    And I convert content with wikilinks
      | content                                    | wikilinks                                                    |
      | See [[Test Page\|my custom link]] here    | [{"note_name": "Test Page", "alias": "my custom link"}]     |
    Then the content should contain "[my custom link](@page-123)"
    And no broken links should be reported

  Scenario: Handle broken wikilinks
    Given I have a WikilinkConverter instance
    When I convert content with wikilinks
      | content                                  | wikilinks                              |
      | This links to [[Unknown Page]] here     | [{"note_name": "Unknown Page"}]       |
    Then the content should contain "(link not found)"
    And broken links should be reported

  Scenario: Convert wikilinks with sections
    Given I have a WikilinkConverter instance
    When I add pages to the cache
      | title      | page_id    |
      | Test Page  | page-123   |
    And I convert content with wikilinks
      | content                                       | wikilinks                                                        |
      | See [[Test Page#Introduction]] for details   | [{"note_name": "Test Page", "section": "Introduction"}]         |
    Then the content should contain "[Test Page#Introduction](@page-123)"
    And no broken links should be reported

  Scenario: Generate broken links report
    Given I have a WikilinkConverter instance
    When I convert content with broken wikilinks
      | content                              | wikilinks                           |
      | Link to [[Missing Page]]             | [{"note_name": "Missing Page"}]    |
      | Another [[Gone Page]] reference      | [{"note_name": "Gone Page"}]       |
    Then the broken links report should list all missing pages

  Scenario: Parse content with mixed links
    Given I have a WikilinkConverter instance with cached pages
    When I parse content "[Valid Page](@page-123) and [Another](@page-456)"
    Then I should get rich text objects with mentions and text

  Scenario: Create Notion mention rich text
    Given I have a WikilinkConverter instance
    When I create a mention for page "page-123" with text "Test Page"
    Then I should get a valid Notion mention object
