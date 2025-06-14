"""Unit tests for the updated WikilinkConverter implementation."""

import unittest
from typing import Any, Dict, List

from obsidian_to_notion.transformers.wikilink_converter import WikilinkConverter


class TestWikilinkConverterNew(unittest.TestCase):
    """Test the updated WikilinkConverter class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.converter = WikilinkConverter()

        # Add some test pages to cache
        self.converter.add_page_to_cache("Test Page", "page-123")
        self.converter.add_page_to_cache("Another Note", "page-456")

    def test_init_with_no_mapping(self) -> None:
        """Test initialization without page mapping."""
        converter = WikilinkConverter()
        self.assertEqual(converter.page_mapping, {})
        self.assertEqual(converter.page_cache, {})
        self.assertEqual(converter.broken_links, [])

    def test_init_with_mapping(self) -> None:
        """Test initialization with page mapping."""
        mapping = {"Page A": "page-a", "Page B": "page-b"}
        converter = WikilinkConverter(mapping)
        self.assertEqual(converter.page_mapping, mapping)
        self.assertEqual(converter.page_cache, {})
        self.assertEqual(converter.broken_links, [])

    def test_add_page_to_cache(self) -> None:
        """Test adding page to cache."""
        converter = WikilinkConverter()
        converter.add_page_to_cache("New Page", "page-789")

        self.assertEqual(converter.page_cache["new page"], "page-789")
        self.assertEqual(converter.page_mapping["New Page"], "page-789")

    def test_convert_content_no_links(self) -> None:
        """Test converting content with no wikilinks."""
        content = "This is just plain text without any links."
        wikilinks: List[Dict[str, Any]] = []

        result = self.converter.convert_content(content, wikilinks)
        self.assertEqual(result, content)

    def test_convert_content_with_valid_link(self) -> None:
        """Test converting content with valid wikilink."""
        content = "Check out [[Test Page]] for more info."
        wikilinks = [{"note_name": "Test Page"}]

        result = self.converter.convert_content(content, wikilinks)
        self.assertIn("[Test Page](@page-123)", result)
        self.assertNotIn("[[Test Page]]", result)

    def test_convert_content_with_alias(self) -> None:
        """Test converting content with wikilink alias."""
        content = "See [[Test Page|my custom link]] here."
        wikilinks = [{"note_name": "Test Page", "alias": "my custom link"}]

        result = self.converter.convert_content(content, wikilinks)
        self.assertIn("[my custom link](@page-123)", result)

    def test_convert_content_with_broken_link(self) -> None:
        """Test converting content with broken wikilink."""
        content = "This links to [[Unknown Page]] which doesn't exist."
        wikilinks = [{"note_name": "Unknown Page"}]

        result = self.converter.convert_content(content, wikilinks)
        self.assertIn("Unknown Page (link not found)", result)
        self.assertIn("Unknown Page", self.converter.broken_links)

    def test_convert_content_with_section_link(self) -> None:
        """Test converting content with section link."""
        content = "See [[Test Page#Introduction]] for details."
        wikilinks = [{"note_name": "Test Page", "section": "Introduction"}]

        result = self.converter.convert_content(content, wikilinks)
        self.assertIn("[Test Page#Introduction](@page-123)", result)

    def test_get_broken_links_report_none(self) -> None:
        """Test broken links report when no broken links."""
        report = self.converter.get_broken_links_report()
        self.assertEqual(report, "No broken links found")

    def test_get_broken_links_report_with_links(self) -> None:
        """Test broken links report with broken links."""
        # Add some broken links
        self.converter.broken_links = [
            "Missing Page",
            "Another Missing",
            "Missing Page",
        ]

        report = self.converter.get_broken_links_report()
        self.assertIn("Found 3 broken links:", report)
        self.assertIn("- Another Missing", report)
        self.assertIn("- Missing Page", report)

    def test_create_mention_rich_text(self) -> None:
        """Test creating Notion mention rich text object."""
        result = self.converter.create_mention_rich_text("page-123", "Test Page")

        expected = {
            "type": "mention",
            "mention": {"type": "page", "page": {"id": "page-123"}},
            "annotations": {
                "bold": False,
                "italic": False,
                "strikethrough": False,
                "underline": False,
                "code": False,
                "color": "default",
            },
            "plain_text": "Test Page",
            "href": "https://www.notion.so/page123",
        }

        self.assertEqual(result, expected)

    def test_parse_notion_link_from_content_no_links(self) -> None:
        """Test parsing content with no Notion links."""
        content = "Just plain text here."
        result = self.converter.parse_notion_link_from_content(content)

        expected = [{"type": "text", "text": {"content": "Just plain text here."}}]
        self.assertEqual(result, expected)

    def test_parse_notion_link_from_content_with_links(self) -> None:
        """Test parsing content with Notion links."""
        content = "Check out [Test Page](@page-123) and [Another](@page-456) for info."
        result = self.converter.parse_notion_link_from_content(content)

        self.assertEqual(len(result), 5)  # text, mention, text, mention, text
        self.assertEqual(result[0]["type"], "text")
        self.assertEqual(result[1]["type"], "mention")
        self.assertEqual(result[2]["type"], "text")
        self.assertEqual(result[3]["type"], "mention")
        self.assertEqual(result[4]["type"], "text")

    def test_find_original_link_basic(self) -> None:
        """Test finding original wikilink in content."""
        content = "This has [[Test Page]] in it."
        result = self.converter._find_original_link(content, "Test Page")
        self.assertEqual(result, "[[Test Page]]")

    def test_find_original_link_with_alias(self) -> None:
        """Test finding original wikilink with alias."""
        content = "This has [[Test Page|custom text]] in it."
        result = self.converter._find_original_link(
            content, "Test Page", alias="custom text"
        )
        self.assertEqual(result, "[[Test Page|custom text]]")

    def test_find_original_link_not_found(self) -> None:
        """Test finding original wikilink when not found."""
        content = "This has no links."
        result = self.converter._find_original_link(content, "Test Page")
        self.assertIsNone(result)

    def test_convert_wikilink_to_notion_found(self) -> None:
        """Test converting wikilink to Notion format when found."""
        result = self.converter._convert_wikilink_to_notion("Test Page")
        self.assertEqual(result, "[Test Page](@page-123)")

    def test_convert_wikilink_to_notion_not_found(self) -> None:
        """Test converting wikilink to Notion format when not found."""
        result = self.converter._convert_wikilink_to_notion("Unknown Page")
        self.assertEqual(result, "Unknown Page (link not found)")
        self.assertIn("Unknown Page", self.converter.broken_links)


if __name__ == "__main__":
    unittest.main()
