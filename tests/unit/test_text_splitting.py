"""Unit tests for text splitting functionality."""

import unittest
from typing import List
from unittest.mock import patch

from obsidian_to_notion.config import (
    AppConfig,
    LoggingConfig,
    MigrationConfig,
    NotionConfig,
    VaultConfig,
)
from obsidian_to_notion.main import ObsidianToNotionMigrator


class TestTextSplitting(unittest.TestCase):
    """Test text splitting for Notion's character limits."""

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

    def _extract_paragraph_texts(self, blocks: List[dict]) -> List[str]:
        """Extract text content from paragraph blocks."""
        texts = []
        for block in blocks:
            if block["type"] == "paragraph":
                text = block["paragraph"]["rich_text"][0]["text"]["content"]
                texts.append(text)
        return texts

    def test_short_content_single_block(self):
        """Test that short content creates a single paragraph block."""
        content = (
            "This is a short paragraph that is well under the 2000 character limit."
        )

        blocks = self.migrator._content_to_notion_blocks(content)

        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["type"], "paragraph")
        self.assertEqual(
            blocks[0]["paragraph"]["rich_text"][0]["text"]["content"], content
        )

    def test_long_content_splits(self):
        """Test that content over 2000 chars is split into multiple blocks."""
        # Create content that's definitely over 2000 chars
        long_text = "This is a long paragraph. " * 100  # ~2600 chars

        blocks = self.migrator._content_to_notion_blocks(long_text.strip())

        # Should be split into multiple blocks
        self.assertGreater(len(blocks), 1)

        # Each block should be under 2000 chars
        for block in blocks:
            text = block["paragraph"]["rich_text"][0]["text"]["content"]
            self.assertLessEqual(len(text), 2000)

        # Combined text should equal original
        combined = "".join(self._extract_paragraph_texts(blocks))
        self.assertEqual(combined, long_text.strip())

    def test_exactly_2000_chars(self):
        """Test content that's exactly 2000 characters."""
        # Create exactly 2000 character string
        text = "a" * 2000

        blocks = self.migrator._content_to_notion_blocks(text)

        # Should be a single block
        self.assertEqual(len(blocks), 1)
        self.assertEqual(
            len(blocks[0]["paragraph"]["rich_text"][0]["text"]["content"]), 2000
        )

    def test_multiline_content_preserved(self):
        """Test that line breaks are preserved within chunks."""
        content = "Line 1: First line\nLine 2: Second line\nLine 3: Third line"

        blocks = self.migrator._content_to_notion_blocks(content)

        # Should preserve line breaks
        self.assertEqual(len(blocks), 1)
        text = blocks[0]["paragraph"]["rich_text"][0]["text"]["content"]
        self.assertIn("\n", text)
        self.assertEqual(text.count("\n"), 2)

    def test_multiline_long_content_splits_properly(self):
        """Test that long multiline content is split without breaking lines."""
        # Create multiline content that will need splitting
        lines = []
        for i in range(50):
            lines.append(
                f"Line {i}: This is a line of text that contains some content."
            )
        content = "\n".join(lines)  # This will be over 2000 chars

        blocks = self.migrator._content_to_notion_blocks(content)

        # Should be split into multiple blocks
        self.assertGreater(len(blocks), 1)

        # Verify no line is split across blocks
        # When content is split, we need to reconstruct with proper joining
        texts = self._extract_paragraph_texts(blocks)

        # The blocks should preserve the content but might not have trailing newlines
        # between chunks, so we check that all content is preserved
        all_text = ""
        for i, text in enumerate(texts):
            all_text += text
            # Add newline between blocks if the current block doesn't end with one
            # and there's a next block
            if i < len(texts) - 1 and not text.endswith("\n"):
                all_text += "\n"

        # Remove any trailing newline that might have been added
        all_text = all_text.rstrip("\n")
        content = content.rstrip("\n")

        self.assertEqual(all_text, content)

        # Each block should contain complete lines
        for i in range(len(blocks) - 1):
            current_block_text = blocks[i]["paragraph"]["rich_text"][0]["text"][
                "content"
            ]
            next_block_text = blocks[i + 1]["paragraph"]["rich_text"][0]["text"][
                "content"
            ]

            # Current block should not end mid-line
            if current_block_text:
                # Either ends with a newline or is the complete text
                self.assertTrue(
                    current_block_text.endswith("\n")
                    or not next_block_text
                    or i == len(blocks) - 2
                )

    def test_empty_lines_between_paragraphs(self):
        """Test handling of empty lines between paragraphs."""
        content = "First paragraph\n\n\nSecond paragraph\n\nThird paragraph"

        blocks = self.migrator._content_to_notion_blocks(content)

        # Empty lines should create separate paragraph blocks
        self.assertEqual(len(blocks), 3)

        texts = self._extract_paragraph_texts(blocks)
        self.assertEqual(texts[0], "First paragraph")
        self.assertEqual(texts[1], "Second paragraph")
        self.assertEqual(texts[2], "Third paragraph")

    def test_very_long_content_multiple_splits(self):
        """Test content requiring multiple splits (>4000 chars)."""
        # Create very long content
        very_long_text = "This is a sentence. " * 300  # ~6000 chars

        blocks = self.migrator._content_to_notion_blocks(very_long_text.strip())

        # Should create at least 3 blocks
        self.assertGreaterEqual(len(blocks), 3)

        # Each block under limit
        for block in blocks:
            text = block["paragraph"]["rich_text"][0]["text"]["content"]
            self.assertLessEqual(len(text), 2000)

        # Combined equals original
        combined = "".join(self._extract_paragraph_texts(blocks))
        self.assertEqual(combined, very_long_text.strip())

    def test_special_characters_handling(self):
        """Test that special characters are handled correctly."""
        content = "Special chars: émojis 🎉🚀, symbols ™®©, quotes \"''\""

        blocks = self.migrator._content_to_notion_blocks(content)

        # Should preserve all special characters
        self.assertEqual(len(blocks), 1)
        text = blocks[0]["paragraph"]["rich_text"][0]["text"]["content"]
        self.assertIn("🎉", text)
        self.assertIn("™", text)
        self.assertIn("'", text)

    def test_long_special_char_content(self):
        """Test splitting content with special characters."""
        # Create long content with special chars
        base = "Text with émojis 🎉 and symbols ™®© and quotes. "
        long_content = base * 50  # Make it long enough to split

        blocks = self.migrator._content_to_notion_blocks(long_content.strip())

        # Should split properly
        self.assertGreater(len(blocks), 1)

        # Special chars should be preserved
        all_text = "".join(self._extract_paragraph_texts(blocks))
        self.assertIn("🎉", all_text)
        self.assertEqual(all_text.count("🎉"), long_content.count("🎉"))

    def test_mixed_paragraph_lengths(self):
        """Test content with mixed short and long paragraphs."""
        content = (
            "Short paragraph.\n\n"
            + ("This is a very long paragraph. " * 100)
            + "\n\n"  # ~3000 chars
            + "Another short paragraph."
        )

        blocks = self.migrator._content_to_notion_blocks(content)

        # Should have at least 4 blocks (short, long split into 2+, short)
        self.assertGreaterEqual(len(blocks), 4)

        # First and last should be short
        self.assertEqual(
            blocks[0]["paragraph"]["rich_text"][0]["text"]["content"],
            "Short paragraph.",
        )
        self.assertEqual(
            blocks[-1]["paragraph"]["rich_text"][0]["text"]["content"],
            "Another short paragraph.",
        )

    def test_trailing_whitespace_handling(self):
        """Test that trailing whitespace is handled correctly."""
        content = "  Text with spaces  \n  \n  Another line  "

        blocks = self.migrator._content_to_notion_blocks(content)

        # Should strip lines and handle empty lines
        self.assertEqual(len(blocks), 2)
        self.assertEqual(
            blocks[0]["paragraph"]["rich_text"][0]["text"]["content"],
            "Text with spaces",
        )
        self.assertEqual(
            blocks[1]["paragraph"]["rich_text"][0]["text"]["content"], "Another line"
        )

    def test_single_very_long_line(self):
        """Test a single line that exceeds 2000 characters."""
        # Create a single line over 2000 chars (no newlines)
        long_line = "a" * 2500

        blocks = self.migrator._content_to_notion_blocks(long_line)

        # Should split into multiple blocks
        self.assertEqual(len(blocks), 2)

        # First block should be ~1900 chars
        self.assertLessEqual(
            len(blocks[0]["paragraph"]["rich_text"][0]["text"]["content"]), 2000
        )
        self.assertGreater(
            len(blocks[0]["paragraph"]["rich_text"][0]["text"]["content"]), 1800
        )

        # Combined should equal original
        combined = "".join(self._extract_paragraph_texts(blocks))
        self.assertEqual(combined, long_line)


if __name__ == "__main__":
    unittest.main()
