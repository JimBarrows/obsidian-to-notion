"""Unit tests for metadata mapping functionality."""

import unittest
from unittest.mock import patch

from obsidian_to_notion.config import (
    AppConfig,
    LoggingConfig,
    MigrationConfig,
    NotionConfig,
    VaultConfig,
)
from obsidian_to_notion.main import ObsidianToNotionMigrator


class TestMetadataMapping(unittest.TestCase):
    """Test metadata to Notion property mapping."""

    def setUp(self):
        """Set up test configuration."""
        self.config = AppConfig(
            vault=VaultConfig(path="/test/vault"),
            notion=NotionConfig(token="test-token", database_id="test-db"),
            migration=MigrationConfig(),
            logging=LoggingConfig(),
        )
        with patch("obsidian_to_notion.main.ObsidianVaultProcessor"), patch(
            "obsidian_to_notion.main.NotionMigrationClient"
        ), patch("obsidian_to_notion.main.DeduplicationManager"), patch(
            "obsidian_to_notion.main.WikilinkConverter"
        ):
            self.migrator = ObsidianToNotionMigrator(self.config)

    def test_tags_list_to_multi_select(self):
        """Test converting list of tags to multi_select property."""
        file_info = {
            "path": "notes/test.md",
            "title": "Test Note",
            "content": "Test content",
            "metadata": {"tags": ["python", "testing", "automation"]},
            "wikilinks": [],
        }

        properties = self.migrator._prepare_notion_properties(file_info)

        self.assertIn("Tags", properties)
        self.assertEqual(
            properties["Tags"]["multi_select"],
            [
                {"name": "python"},
                {"name": "testing"},
                {"name": "automation"},
            ],
        )

    def test_tags_string_to_multi_select(self):
        """Test converting comma-separated tags to multi_select property."""
        file_info = {
            "path": "notes/test.md",
            "title": "Test Note",
            "content": "Test content",
            "metadata": {"tags": "python, testing, automation"},
            "wikilinks": [],
        }

        properties = self.migrator._prepare_notion_properties(file_info)

        self.assertIn("Tags", properties)
        self.assertEqual(
            properties["Tags"]["multi_select"],
            [
                {"name": "python"},
                {"name": "testing"},
                {"name": "automation"},
            ],
        )

    def test_single_tag_to_multi_select(self):
        """Test converting single tag to multi_select property."""
        file_info = {
            "path": "notes/test.md",
            "title": "Test Note",
            "content": "Test content",
            "metadata": {"tags": "python"},
            "wikilinks": [],
        }

        properties = self.migrator._prepare_notion_properties(file_info)

        self.assertIn("Tags", properties)
        self.assertEqual(
            properties["Tags"]["multi_select"],
            [
                {"name": "python"},
            ],
        )

    def test_directory_from_file_path(self):
        """Test extracting directory from file path."""
        file_info = {
            "path": "projects/web/frontend/index.md",
            "title": "Frontend Index",
            "content": "Test content",
            "metadata": {},
            "wikilinks": [],
        }

        properties = self.migrator._prepare_notion_properties(file_info)

        self.assertIn("Directory", properties)
        self.assertEqual(
            properties["Directory"]["rich_text"][0]["text"]["content"],
            "projects/web/frontend",
        )

    def test_url_metadata_mapping(self):
        """Test URL metadata mapping."""
        file_info = {
            "path": "bookmarks/article.md",
            "title": "Interesting Article",
            "content": "Test content",
            "metadata": {"url": "https://example.com/article"},
            "wikilinks": [],
        }

        properties = self.migrator._prepare_notion_properties(file_info)

        self.assertIn("URL", properties)
        self.assertEqual(properties["URL"]["url"], "https://example.com/article")

    def test_type_metadata_mapping(self):
        """Test type metadata mapping."""
        file_info = {
            "path": "notes/meeting.md",
            "title": "Team Meeting",
            "content": "Test content",
            "metadata": {"type": "meeting-notes"},
            "wikilinks": [],
        }

        properties = self.migrator._prepare_notion_properties(file_info)

        self.assertIn("Type", properties)
        self.assertEqual(
            properties["Type"]["rich_text"][0]["text"]["content"], "meeting-notes"
        )

    def test_modified_date_mapping(self):
        """Test modified date mapping."""
        file_info = {
            "path": "notes/test.md",
            "title": "Test Note",
            "content": "Test content",
            "metadata": {"modified": "2024-01-15T10:30:00Z"},
            "wikilinks": [],
        }

        properties = self.migrator._prepare_notion_properties(file_info)

        self.assertIn("Modified", properties)
        self.assertEqual(
            properties["Modified"]["date"]["start"], "2024-01-15T10:30:00Z"
        )

    def test_date_fallback_for_modified(self):
        """Test using date field when modified is not present."""
        file_info = {
            "path": "notes/test.md",
            "title": "Test Note",
            "content": "Test content",
            "metadata": {"date": "2024-01-10T08:00:00Z"},
            "wikilinks": [],
        }

        properties = self.migrator._prepare_notion_properties(file_info)

        self.assertIn("Modified", properties)
        self.assertEqual(
            properties["Modified"]["date"]["start"], "2024-01-10T08:00:00Z"
        )

    def test_all_metadata_fields_together(self):
        """Test handling all metadata fields together."""
        file_info = {
            "path": "projects/python/app.md",
            "title": "Python App Documentation",
            "content": "Test content",
            "metadata": {
                "tags": ["python", "backend", "api"],
                "url": "https://github.com/user/project",
                "type": "documentation",
                "modified": "2024-01-20T14:00:00Z",
            },
            "wikilinks": [],
        }

        properties = self.migrator._prepare_notion_properties(file_info)

        # Check all properties
        self.assertIn("Tags", properties)
        self.assertEqual(len(properties["Tags"]["multi_select"]), 3)

        self.assertIn("Directory", properties)
        self.assertEqual(
            properties["Directory"]["rich_text"][0]["text"]["content"],
            "projects/python",
        )

        self.assertIn("URL", properties)
        self.assertEqual(properties["URL"]["url"], "https://github.com/user/project")

        self.assertIn("Type", properties)
        self.assertEqual(
            properties["Type"]["rich_text"][0]["text"]["content"], "documentation"
        )

        self.assertIn("Modified", properties)
        self.assertEqual(
            properties["Modified"]["date"]["start"], "2024-01-20T14:00:00Z"
        )

    def test_empty_metadata(self):
        """Test handling files with no metadata."""
        file_info = {
            "path": "notes/simple.md",
            "title": "Simple Note",
            "content": "Test content",
            "metadata": {},
            "wikilinks": [],
        }

        properties = self.migrator._prepare_notion_properties(file_info)

        # Should still have Name and Directory
        self.assertIn("Name", properties)
        self.assertIn("Directory", properties)

        # Should not have optional metadata fields
        self.assertNotIn("Tags", properties)
        self.assertNotIn("URL", properties)
        self.assertNotIn("Type", properties)
        self.assertNotIn("Modified", properties)

    def test_empty_tags_handling(self):
        """Test handling empty tags."""
        file_info = {
            "path": "notes/test.md",
            "title": "Test Note",
            "content": "Test content",
            "metadata": {"tags": []},
            "wikilinks": [],
        }

        properties = self.migrator._prepare_notion_properties(file_info)

        # Empty tags list should create empty multi_select
        self.assertIn("Tags", properties)
        self.assertEqual(properties["Tags"]["multi_select"], [])

    def test_whitespace_in_tags(self):
        """Test handling tags with extra whitespace."""
        file_info = {
            "path": "notes/test.md",
            "title": "Test Note",
            "content": "Test content",
            "metadata": {"tags": "  python  ,   testing  ,  automation  "},
            "wikilinks": [],
        }

        properties = self.migrator._prepare_notion_properties(file_info)

        # Tags should be trimmed
        self.assertIn("Tags", properties)
        self.assertEqual(
            properties["Tags"]["multi_select"],
            [
                {"name": "python"},
                {"name": "testing"},
                {"name": "automation"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
