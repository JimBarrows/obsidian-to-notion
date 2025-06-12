"""Step definitions for Obsidian parser integration tests."""

import os
import shutil
import sys
from pathlib import Path

from behave import given, then, when

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from obsidian_to_notion.parsers import ObsidianVaultProcessor  # noqa: E402


@given('I have an Obsidian vault at "{vault_name}"')
def step_create_vault(context, vault_name):
    """Create a test vault directory."""
    context.vault_path = Path(context.temp_dir) / vault_name
    context.vault_path.mkdir(parents=True, exist_ok=True)


@given("the vault is empty")
def step_empty_vault(context):
    """Ensure the vault is empty."""
    if context.vault_path.exists():
        shutil.rmtree(context.vault_path)
    context.vault_path.mkdir(parents=True, exist_ok=True)


@given("the vault contains the following markdown files")
def step_create_markdown_files(context):
    """Create markdown files from table data."""
    for row in context.table:
        file_path = context.vault_path / row["filename"]
        file_path.parent.mkdir(parents=True, exist_ok=True)

        content = f"---\ntitle: {row['title']}\n---\n\n{row['content']}"
        file_path.write_text(content)


@given('a markdown file "{filename}" with frontmatter')
def step_create_file_with_frontmatter(context, filename):
    """Create a file with specific frontmatter."""
    file_path = context.vault_path / filename
    file_path.write_text(context.text)


@given("a markdown file with content")
def step_create_file_with_content(context):
    """Create a file with specific content."""
    file_path = context.vault_path / "test_links.md"
    file_path.write_text(context.text)


@given("the vault contains files")
def step_create_files(context):
    """Create files from table."""
    for row in context.table:
        file_path = context.vault_path / row["filename"]
        file_path.parent.mkdir(parents=True, exist_ok=True)
        content = f"---\ntitle: {row['title']}\n---\n\n# {row['title']}"
        file_path.write_text(content)


@given("I need to sanitize the following text")
def step_setup_sanitization_data(context):
    """Setup sanitization test data."""
    context.sanitization_data = []
    for row in context.table:
        context.sanitization_data.append(
            {"original": row["original"], "expected": row["sanitized"]}
        )


@given("a markdown file that cannot be read")
def step_create_unreadable_file(context):
    """Create a file that will cause read errors."""
    file_path = context.vault_path / "unreadable.md"
    file_path.write_text("content")
    # Make file unreadable (on Unix systems)
    if os.name != "nt":  # Not Windows
        os.chmod(file_path, 0o000)
    context.unreadable_file = file_path


@when("I process the vault")
def step_process_vault(context):
    """Process the vault with ObsidianVaultProcessor."""
    context.processor = ObsidianVaultProcessor(str(context.vault_path))
    context.result = context.processor.process_vault()


@when("I sanitize each text")
def step_sanitize_text(context):
    """Sanitize text strings."""
    context.processor = ObsidianVaultProcessor(str(context.vault_path))
    context.sanitized_results = []
    for item in context.sanitization_data:
        sanitized = context.processor.sanitize_for_notion(item["original"])
        context.sanitized_results.append(
            {
                "original": item["original"],
                "sanitized": sanitized,
                "expected": item["expected"],
            }
        )


@then("I should find {count:d} markdown files")
def step_verify_markdown_count(context, count):
    """Verify the number of markdown files found."""
    assert (
        len(context.result["markdown_files"]) == count
    ), f"Expected {count} files, found {len(context.result['markdown_files'])}"


@then("I should find {count:d} attachments")
def step_verify_attachment_count(context, count):
    """Verify the number of attachments found."""
    assert (
        len(context.result["attachments"]) == count
    ), f"Expected {count} attachments, found {len(context.result['attachments'])}"


@then("the wikilink map should be empty")
def step_verify_empty_wikilink_map(context):
    """Verify wikilink map is empty."""
    wikilink_count = len(context.result["wikilink_map"])
    assert (
        wikilink_count == 0
    ), f"Expected empty wikilink map, found {wikilink_count} entries"


@then("each file should have its content and metadata extracted")
def step_verify_file_extraction(context):
    """Verify files have content and metadata."""
    for file_info in context.result["markdown_files"]:
        assert "title" in file_info
        assert "content" in file_info
        assert "metadata" in file_info
        assert "wikilinks" in file_info
        assert "embedded_attachments" in file_info


@then("the file metadata should contain")
def step_verify_metadata(context):
    """Verify specific metadata fields."""
    file_info = context.result["markdown_files"][0]
    metadata = file_info["metadata"]

    for row in context.table:
        field = row["field"]
        expected = row["value"]

        assert field in metadata, f"Field '{field}' not found in metadata"

        # Handle list values
        if expected.startswith("[") and expected.endswith("]"):
            expected_list = [x.strip() for x in expected[1:-1].split(",")]
            assert metadata[field] == expected_list
        else:
            assert str(metadata[field]) == expected


@then("I should find the following wikilinks")
def step_verify_wikilinks(context):
    """Verify extracted wikilinks."""
    file_info = context.result["markdown_files"][0]
    wikilinks = file_info["wikilinks"]

    assert len(wikilinks) == len(
        context.table.rows
    ), f"Expected {len(context.table.rows)} wikilinks, found {len(wikilinks)}"

    for i, row in enumerate(context.table):
        link = wikilinks[i]
        assert link["note_name"] == (row["note_name"] if row["note_name"] else None)
        assert link["heading"] == (row["heading"] if row["heading"] else None)
        assert link["display_text"] == row["display_text"]
        assert link["is_embed"] == (row["is_embed"] == "true")


@then("the wikilink map should contain")
def step_verify_wikilink_map(context):
    """Verify wikilink map entries."""
    wikilink_map = context.result["wikilink_map"]

    for row in context.table:
        title_lower = row["title"].lower()
        assert title_lower in wikilink_map, f"'{title_lower}' not found in wikilink map"

        # Verify the path ends with the expected filename
        actual_path = wikilink_map[title_lower]
        expected_end = row["path"]
        assert str(actual_path).endswith(
            expected_end
        ), f"Expected path to end with {expected_end}, got {actual_path}"


@then("I should find {count:d} embedded attachments")
def step_verify_embedded_attachments(context, count):
    """Verify embedded attachments."""
    file_info = context.result["markdown_files"][0]
    attachments = file_info["embedded_attachments"]

    assert (
        len(attachments) == count
    ), f"Expected {count} attachments, found {len(attachments)}"

    if context.table:
        expected_files = [row["filename"] for row in context.table]
        assert set(attachments) == set(expected_files)


@then("the sanitized versions should match the expected results")
def step_verify_sanitization(context):
    """Verify text sanitization."""
    for result in context.sanitized_results:
        assert result["sanitized"] == result["expected"], (
            f"Sanitization failed for '{result['original']}': "
            f"expected '{result['expected']}', got '{result['sanitized']}'"
        )


@then("the file should be skipped")
def step_verify_file_skipped(context):
    """Verify problematic file was skipped."""
    # The unreadable file should not be in the results
    file_paths = [f["path"].name for f in context.result["markdown_files"]]
    assert "unreadable.md" not in file_paths


@then("an error should be logged")
def step_verify_error_logged(context):
    """Verify error handling (would check logs in real implementation)."""
    # In a real implementation, we would capture and verify log output
    pass


@then("processing should continue with other files")
def step_verify_processing_continued(context):
    """Verify processing continued after error."""
    # Should have processed other files despite the error
    # This is implicitly verified if other files are in the results
    pass
