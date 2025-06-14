"""Unit tests for ObsidianVaultProcessor."""

import shutil
import tempfile
import unittest
from pathlib import Path

from obsidian_to_notion.parsers import ObsidianVaultProcessor


class TestObsidianVaultProcessor(unittest.TestCase):
    """Test cases for ObsidianVaultProcessor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.vault_path = Path(self.temp_dir) / "test_vault"
        self.vault_path.mkdir(parents=True)
        self.processor = ObsidianVaultProcessor(str(self.vault_path))

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_init(self):
        """Test processor initialization."""
        processor = ObsidianVaultProcessor("/path/to/vault")

        self.assertEqual(processor.vault_path, Path("/path/to/vault"))
        self.assertEqual(processor.markdown_files, [])
        self.assertEqual(processor.attachments, [])
        self.assertEqual(processor.wikilink_map, {})

    def test_process_vault_not_exists(self):
        """Test processing non-existent vault."""
        processor = ObsidianVaultProcessor("/non/existent/path")

        with self.assertRaises(FileNotFoundError) as context:
            processor.process_vault()

        self.assertIn("Vault path does not exist", str(context.exception))

    def test_process_empty_vault(self):
        """Test processing empty vault."""
        result = self.processor.process_vault()

        self.assertEqual(len(result["markdown_files"]), 0)
        self.assertEqual(len(result["attachments"]), 0)
        self.assertEqual(len(result["wikilink_map"]), 0)

    def test_process_markdown_file_with_frontmatter(self):
        """Test processing markdown file with frontmatter."""
        # Create test file
        test_file = self.vault_path / "test.md"
        test_file.write_text(
            """---
title: Test Document
tags: [test, unit]
date: 2024-01-15
---

# Test Content

This is a test document with [[wikilink]]."""
        )

        file_info = self.processor.process_markdown_file(test_file)

        self.assertEqual(file_info["title"], "Test Document")
        self.assertEqual(file_info["metadata"]["tags"], ["test", "unit"])
        self.assertEqual(str(file_info["metadata"]["date"]), "2024-01-15")
        self.assertIn("Test Content", file_info["content"])
        self.assertEqual(len(file_info["wikilinks"]), 1)

    def test_process_markdown_file_without_frontmatter(self):
        """Test processing markdown file without frontmatter."""
        test_file = self.vault_path / "simple.md"
        test_file.write_text("# Simple Document\n\nNo frontmatter here.")

        file_info = self.processor.process_markdown_file(test_file)

        self.assertEqual(file_info["title"], "simple")  # From filename
        self.assertEqual(file_info["metadata"], {})
        self.assertIn("Simple Document", file_info["content"])

    def test_process_markdown_file_error_handling(self):
        """Test error handling in file processing."""
        # Create a path that doesn't exist
        fake_file = self.vault_path / "fake.md"

        result = self.processor.process_markdown_file(fake_file)

        self.assertIsNone(result)

    def test_extract_wikilinks_basic(self):
        """Test extraction of basic wikilinks."""
        content = "This has a [[Basic Link]] in it."

        links = self.processor.extract_wikilinks(content)

        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["note_name"], "Basic Link")
        self.assertEqual(links[0]["display_text"], "Basic Link")
        self.assertFalse(links[0]["is_embed"])
        self.assertIsNone(links[0]["heading"])

    def test_extract_wikilinks_with_alias(self):
        """Test extraction of wikilinks with aliases."""
        content = "Link with [[Original|Display Text]] alias."

        links = self.processor.extract_wikilinks(content)

        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["note_name"], "Original")
        self.assertEqual(links[0]["display_text"], "Display Text")

    def test_extract_wikilinks_with_heading(self):
        """Test extraction of wikilinks with headings."""
        content = "Link to [[Note#Section]] with heading."

        links = self.processor.extract_wikilinks(content)

        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["note_name"], "Note")
        self.assertEqual(links[0]["heading"], "Section")

    def test_extract_wikilinks_with_heading_and_alias(self):
        """Test extraction of complex wikilinks."""
        content = "Complex [[Note#Section|Custom Display]] link."

        links = self.processor.extract_wikilinks(content)

        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["note_name"], "Note")
        self.assertEqual(links[0]["heading"], "Section")
        self.assertEqual(links[0]["display_text"], "Custom Display")

    def test_extract_wikilinks_embedded(self):
        """Test extraction of embedded wikilinks."""
        content = "Embedded ![[Image.png]] and ![[Document.pdf]]."

        links = self.processor.extract_wikilinks(content)

        self.assertEqual(len(links), 2)
        self.assertTrue(links[0]["is_embed"])
        self.assertTrue(links[1]["is_embed"])
        self.assertEqual(links[0]["note_name"], "Image.png")
        self.assertEqual(links[1]["note_name"], "Document.pdf")

    def test_extract_wikilinks_multiple(self):
        """Test extraction of multiple wikilinks."""
        content = """
        Multiple links: [[First]], [[Second|Alias]], [[Third#Section]],
        ![[Embedded]], and [[Fourth#Part|Display]].
        """

        links = self.processor.extract_wikilinks(content)

        self.assertEqual(len(links), 5)
        # Verify each link type is captured correctly
        link_types = [(link["note_name"], link["is_embed"]) for link in links]
        expected = [
            ("First", False),
            ("Second", False),
            ("Third", False),
            ("Embedded", True),
            ("Fourth", False),
        ]
        self.assertEqual(link_types, expected)

    def test_extract_embedded_attachments(self):
        """Test extraction of embedded attachments."""
        content = """
        # Document

        ![[presentation.pdf]]
        ![[image.PNG]]
        ![[data.xlsx]]

        Regular [[wikilink]] not included.
        """

        attachments = self.processor.extract_embedded_attachments(content)

        self.assertEqual(len(attachments), 3)
        self.assertIn("presentation.pdf", attachments)
        self.assertIn("image.PNG", attachments)
        self.assertIn("data.xlsx", attachments)

    def test_extract_embedded_attachments_case_insensitive(self):
        """Test case-insensitive attachment detection."""
        content = "![[Image.PNG]] ![[photo.JpG]] ![[doc.PDF]]"

        attachments = self.processor.extract_embedded_attachments(content)

        self.assertEqual(len(attachments), 3)

    def test_sanitize_for_notion_basic(self):
        """Test basic text sanitization."""
        test_cases = [
            ("Normal Text", "Normal Text"),
            ("Text*With*Asterisks", "TextWithAsterisks"),
            ("Path/To/File", "Path-To-File"),
            ("Question?Mark", "QuestionMark"),
            ("Colon:Here", "Colon-Here"),
        ]

        for original, expected in test_cases:
            result = self.processor.sanitize_for_notion(original)
            self.assertEqual(result, expected)

    def test_sanitize_for_notion_special_chars(self):
        """Test sanitization of special characters."""
        text = "File<Name>With|Special?Chars*"
        result = self.processor.sanitize_for_notion(text)

        self.assertEqual(result, "FileNameWith-SpecialChars")

    def test_sanitize_for_notion_backslashes(self):
        """Test sanitization of backslashes."""
        text = "Path\\To\\Windows\\File"
        result = self.processor.sanitize_for_notion(text)

        self.assertEqual(result, "Path-To-Windows-File")

    def test_sanitize_for_notion_whitespace(self):
        """Test sanitization preserves regular spaces."""
        text = "Text with   multiple   spaces"
        result = self.processor.sanitize_for_notion(text)

        # Regular spaces should be preserved
        self.assertEqual(result, "Text with   multiple   spaces")

    def test_sanitize_for_notion_non_breaking_space(self):
        """Test sanitization of non-breaking spaces."""
        text = "Text\u00a0with\u00a0non-breaking\u00a0spaces"
        result = self.processor.sanitize_for_notion(text)

        self.assertEqual(result, "Text with non-breaking spaces")

    def test_process_vault_integration(self):
        """Test full vault processing integration."""
        # Create test structure
        (self.vault_path / "note1.md").write_text(
            """---
title: First Note
---

Content with [[link]]."""
        )

        (self.vault_path / "subdir").mkdir()
        (self.vault_path / "subdir" / "note2.md").write_text(
            "# Second Note\n\n![[image.png]]"
        )

        (self.vault_path / "image.png").write_bytes(b"fake image data")
        (self.vault_path / "document.pdf").write_bytes(b"fake pdf data")

        # Process vault
        result = self.processor.process_vault()

        # Verify results
        self.assertEqual(len(result["markdown_files"]), 2)
        self.assertEqual(len(result["attachments"]), 2)
        self.assertEqual(len(result["wikilink_map"]), 2)

        # Check wikilink map
        self.assertIn("first note", result["wikilink_map"])
        self.assertIn("note2", result["wikilink_map"])

    def test_wikilink_map_case_insensitive(self):
        """Test wikilink map uses lowercase keys."""
        test_file = self.vault_path / "MixedCase.md"
        test_file.write_text(
            """---
title: Mixed Case Title
---

Content here."""
        )

        self.processor.process_markdown_file(test_file)

        self.assertIn("mixed case title", self.processor.wikilink_map)
        self.assertNotIn("Mixed Case Title", self.processor.wikilink_map)

    def test_extract_wikilinks(self):
        """Test extraction of various wikilink formats as specified in issue #6."""
        processor = ObsidianVaultProcessor("/tmp")

        content = (
            "This is a [[basic link]] and [[link with|display text]] and ![[embedded]]"
        )
        wikilinks = processor.extract_wikilinks(content)

        assert len(wikilinks) == 3
        assert wikilinks[0]["note_name"] == "basic link"
        assert wikilinks[1]["display_text"] == "display text"
        assert wikilinks[2]["is_embed"] is True

    def test_sanitize_for_notion(self):
        """Test text sanitization for Notion compatibility as specified in issue #6."""
        processor = ObsidianVaultProcessor("/tmp")

        dirty_text = "File/with\\bad:chars|and*stuff"
        clean_text = processor.sanitize_for_notion(dirty_text)

        assert "/" not in clean_text
        assert "\\" not in clean_text
        assert "*" not in clean_text

    def test_process_file_with_template_placeholders(self):
        """Test processing file with template placeholders in YAML."""
        test_file = self.vault_path / "template.md"
        test_file.write_text(
            """---
author: {{author}}
title: {{title}}
date: {{date}}
tags: [{{tag1}}, {{tag2}}]
---

# Template Document

This document has template placeholders."""
        )

        file_info = self.processor.process_markdown_file(test_file)

        # File should be processed despite template placeholders
        self.assertIsNotNone(file_info)
        self.assertEqual(file_info["title"], "template")  # From filename
        self.assertIn("Template Document", file_info["content"])
        # Metadata might be empty or contain placeholders as strings
        self.assertIsInstance(file_info["metadata"], dict)

    def test_process_file_with_yaml_tabs(self):
        """Test processing file with tabs in YAML frontmatter."""
        test_file = self.vault_path / "tabs.md"
        test_file.write_text(
            """---
author:
\t- [[Robert Turnbull]]
\t- [[John Doe]]
title: Document with Tabs
---

# Content
The YAML has tab characters."""
        )

        file_info = self.processor.process_markdown_file(test_file)

        # File should be processed despite tabs in YAML
        self.assertIsNotNone(file_info)
        self.assertIn("Content", file_info["content"])

    def test_process_file_with_missing_colon_space(self):
        """Test processing file with missing space after colon in YAML."""
        test_file = self.vault_path / "missing_space.md"
        test_file.write_text(
            """---
business name:Copart
location:USA
employees:7000
---

# Business Info
Missing spaces after colons."""
        )

        file_info = self.processor.process_markdown_file(test_file)

        # File should be processed despite YAML syntax errors
        self.assertIsNotNone(file_info)
        self.assertIn("Business Info", file_info["content"])

    def test_process_file_with_markdown_in_yaml(self):
        """Test processing file with markdown links in YAML values."""
        test_file = self.vault_path / "markdown_yaml.md"
        test_file.write_text(
            """---
author: [Kendra Cherry](https://www.verywellmind.com)
source: [Article Link](https://example.com/article)
related: [[Other Note]]
---

# Psychology Article
YAML contains markdown links."""
        )

        file_info = self.processor.process_markdown_file(test_file)

        # File should be processed despite markdown in YAML
        self.assertIsNotNone(file_info)
        self.assertIn("Psychology Article", file_info["content"])

    def test_process_file_with_invalid_yaml_continues(self):
        """Test that invalid YAML doesn't prevent content extraction."""
        test_file = self.vault_path / "invalid.md"
        test_file.write_text(
            """---
this is not valid yaml at all: {{{
another line: [[[
---

# Important Content

This content should still be extracted even if YAML is invalid."""
        )

        file_info = self.processor.process_markdown_file(test_file)

        # Content should still be extracted
        self.assertIsNotNone(file_info)
        self.assertIn("Important Content", file_info["content"])
        self.assertIn("This content should still be extracted", file_info["content"])

    def test_process_vault_with_mixed_valid_invalid_files(self):
        """Test vault processing continues with invalid YAML files."""
        # Create valid file
        valid_file = self.vault_path / "valid.md"
        valid_file.write_text(
            """---
title: Valid Document
author: John Doe
---

# Valid Content
This file has valid YAML."""
        )

        # Create invalid file
        invalid_file = self.vault_path / "invalid.md"
        invalid_file.write_text(
            """---
author: {{author}}
broken: [[[
---

# Invalid YAML File
But content is still good."""
        )

        # Process vault
        result = self.processor.process_vault()

        # Both files should be processed
        self.assertEqual(len(result["markdown_files"]), 2)

        # Verify content was extracted from both
        titles = [f["title"] for f in result["markdown_files"]]
        self.assertIn("Valid Document", titles)
        self.assertIn("invalid", titles)  # Filename used as fallback

    def test_yaml_error_recovery_with_frontmatter_delimiters(self):
        """Test handling of various YAML delimiter issues."""
        test_cases = [
            # Missing closing delimiter
            ("---\ntitle: Test\n\n# Content", True),
            # Extra delimiters
            ("---\ntitle: Test\n---\n---\n# Content", True),
            # No opening delimiter
            ("title: Test\n---\n# Content", True),
        ]

        for idx, (content, should_extract_content) in enumerate(test_cases):
            test_file = self.vault_path / f"delimiter_test_{idx}.md"
            test_file.write_text(content)

            file_info = self.processor.process_markdown_file(test_file)

            if should_extract_content:
                self.assertIsNotNone(file_info)
                self.assertIn("Content", file_info.get("content", ""))

    def test_extract_wikilinks_from_yaml_corrupted_file(self):
        """Test wikilink extraction continues despite YAML errors."""
        test_file = self.vault_path / "yaml_with_links.md"
        test_file.write_text(
            """---
related: [[Note 1]] [[Note 2]]
author: {{author}}
---

# Document

Contains [[Note 3]] and [[Note 4]] in content."""
        )

        file_info = self.processor.process_markdown_file(test_file)

        # Should still extract wikilinks from content
        self.assertIsNotNone(file_info)
        wikilinks = file_info.get("wikilinks", [])
        # Should find at least the content wikilinks
        note_names = [link["note_name"] for link in wikilinks]
        self.assertIn("Note 3", note_names)
        self.assertIn("Note 4", note_names)


if __name__ == "__main__":
    unittest.main()
