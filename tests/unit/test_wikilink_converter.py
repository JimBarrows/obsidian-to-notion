"""Unit tests for wikilink converter module."""

import unittest

from obsidian_to_notion.transformers.wikilink_converter import WikilinkConverter


class TestWikilinkConverter(unittest.TestCase):
    """Test WikilinkConverter class."""

    def setUp(self):
        """Set up test fixtures."""
        self.page_mapping = {
            "Note A": "page-id-a",
            "Note B": "page-id-b",
            "Project/Task": "page-id-task",
        }
        self.converter = WikilinkConverter(self.page_mapping)

    def test_init(self):
        """Test WikilinkConverter initialization."""
        self.assertEqual(self.converter.page_mapping, self.page_mapping)

    def test_convert_wikilink_basic(self):
        """Test converting basic wikilink."""
        result = self.converter.convert_wikilink("[[Note A]]")
        self.assertEqual(
            result, {"type": "mention", "mention": {"page": {"id": "page-id-a"}}}
        )

    def test_convert_wikilink_with_alias(self):
        """Test converting wikilink with alias."""
        result = self.converter.convert_wikilink("[[Note A|Custom Text]]")
        self.assertEqual(
            result, {"type": "mention", "mention": {"page": {"id": "page-id-a"}}}
        )

    def test_convert_wikilink_with_heading(self):
        """Test converting wikilink with heading."""
        result = self.converter.convert_wikilink("[[Note A#Section]]")
        self.assertEqual(
            result, {"type": "mention", "mention": {"page": {"id": "page-id-a"}}}
        )

    def test_convert_wikilink_not_found(self):
        """Test converting wikilink when page not found."""
        result = self.converter.convert_wikilink("[[Unknown Note]]")
        self.assertEqual(
            result,
            {"type": "text", "text": {"content": "[[Unknown Note]]", "link": None}},
        )

    def test_convert_wikilink_empty(self):
        """Test converting empty wikilink."""
        result = self.converter.convert_wikilink("[[]]")
        self.assertEqual(
            result,
            {"type": "text", "text": {"content": "[[]]", "link": None}},
        )

    def test_convert_text_with_links(self):
        """Test converting text with multiple wikilinks."""
        text = "See [[Note A]] and [[Note B]] for details."
        blocks = self.converter.convert_text_with_links(text)

        self.assertEqual(len(blocks), 5)
        self.assertEqual(blocks[0], {"type": "text", "text": {"content": "See "}})
        self.assertEqual(
            blocks[1], {"type": "mention", "mention": {"page": {"id": "page-id-a"}}}
        )
        self.assertEqual(blocks[2], {"type": "text", "text": {"content": " and "}})
        self.assertEqual(
            blocks[3], {"type": "mention", "mention": {"page": {"id": "page-id-b"}}}
        )
        self.assertEqual(
            blocks[4], {"type": "text", "text": {"content": " for details."}}
        )

    def test_convert_text_no_links(self):
        """Test converting text without wikilinks."""
        text = "This is plain text without any links."
        blocks = self.converter.convert_text_with_links(text)

        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0], {"type": "text", "text": {"content": text}})

    def test_convert_text_with_unknown_links(self):
        """Test converting text with unknown wikilinks."""
        text = "See [[Unknown]] page."
        blocks = self.converter.convert_text_with_links(text)

        self.assertEqual(len(blocks), 3)
        self.assertEqual(blocks[0], {"type": "text", "text": {"content": "See "}})
        self.assertEqual(
            blocks[1],
            {"type": "text", "text": {"content": "[[Unknown]]", "link": None}},
        )
        self.assertEqual(blocks[2], {"type": "text", "text": {"content": " page."}})

    def test_create_paragraph_block(self):
        """Test creating paragraph block."""
        text = "This is a paragraph with [[Note A]]."
        block = self.converter.create_paragraph_block(text)

        expected = {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "text": [
                    {"type": "text", "text": {"content": "This is a paragraph with "}},
                    {"type": "mention", "mention": {"page": {"id": "page-id-a"}}},
                    {"type": "text", "text": {"content": "."}},
                ]
            },
        }
        self.assertEqual(block, expected)

    def test_create_heading_block(self):
        """Test creating heading blocks."""
        # Heading 1
        block1 = self.converter.create_heading_block("# Main Title", 1)
        self.assertEqual(block1["type"], "heading_1")
        self.assertEqual(
            block1["heading_1"]["text"][0]["text"]["content"], "Main Title"
        )

        # Heading 2
        block2 = self.converter.create_heading_block("## Sub Title", 2)
        self.assertEqual(block2["type"], "heading_2")
        self.assertEqual(block2["heading_2"]["text"][0]["text"]["content"], "Sub Title")

        # Heading 3
        block3 = self.converter.create_heading_block("### Small Title", 3)
        self.assertEqual(block3["type"], "heading_3")
        self.assertEqual(
            block3["heading_3"]["text"][0]["text"]["content"], "Small Title"
        )

    def test_process_markdown_to_blocks(self):
        """Test processing markdown to Notion blocks."""
        markdown = """# Title
This is a paragraph with [[Note A]].

## Section
Another paragraph with [[Note B|custom text]].
"""
        blocks = self.converter.process_markdown_to_blocks(markdown)

        self.assertEqual(len(blocks), 4)
        self.assertEqual(blocks[0]["type"], "heading_1")
        self.assertEqual(blocks[1]["type"], "paragraph")
        self.assertEqual(blocks[2]["type"], "heading_2")
        self.assertEqual(blocks[3]["type"], "paragraph")

    def test_process_markdown_empty(self):
        """Test processing empty markdown."""
        blocks = self.converter.process_markdown_to_blocks("")
        self.assertEqual(blocks, [])

    def test_process_markdown_only_whitespace(self):
        """Test processing markdown with only whitespace."""
        blocks = self.converter.process_markdown_to_blocks("   \n\n   ")
        self.assertEqual(blocks, [])

    def test_resolve_page_id_found(self):
        """Test resolving page ID when found."""
        page_id = self.converter.resolve_page_id("Note A")
        self.assertEqual(page_id, "page-id-a")

    def test_resolve_page_id_not_found(self):
        """Test resolving page ID when not found."""
        page_id = self.converter.resolve_page_id("Unknown")
        self.assertIsNone(page_id)

    def test_resolve_page_id_empty(self):
        """Test resolving empty page ID."""
        page_id = self.converter.resolve_page_id("")
        self.assertIsNone(page_id)


if __name__ == "__main__":
    unittest.main()
