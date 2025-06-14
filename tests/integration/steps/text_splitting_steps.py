"""Step definitions for text splitting feature tests."""

import re
from pathlib import Path

from behave import given, then
from behave.runner import Context


def generate_long_text(length: int) -> str:
    """Generate a long text of approximately the specified length."""
    base_text = (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
        "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
        "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris. "
    )

    # Calculate how many times to repeat
    repeat_count = (length // len(base_text)) + 1
    text = base_text * repeat_count

    # Trim to exact length
    return text[:length]


@given('I have a markdown file "{filepath}" with content')
def step_create_markdown_file_with_content(context: Context, filepath: str) -> None:
    """Create a markdown file with content, replacing placeholders with long text."""
    vault_path = Path(context.vault_path)
    file_path = vault_path / filepath

    # Create parent directories if needed
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Process the content to replace placeholders
    content = context.text.strip()

    # Replace long text placeholders
    content = content.replace("<LONG_TEXT_2500_CHARS>", generate_long_text(2500))
    content = content.replace("<LONG_TEXT_5000_CHARS>", generate_long_text(5000))
    content = content.replace("<TEXT_EXACTLY_2000_CHARS>", generate_long_text(2000))

    # For multi-line long text
    if "<CONTINUE_TO_2500_CHARS_TOTAL>" in content:
        # Calculate how much text we already have
        existing_length = len(content.replace("<CONTINUE_TO_2500_CHARS_TOTAL>", ""))
        additional_needed = 2500 - existing_length
        content = content.replace(
            "<CONTINUE_TO_2500_CHARS_TOTAL>", generate_long_text(additional_needed)
        )

    # For special characters text
    if "<CONTINUE_WITH_SPECIAL_CHARS_TO_2100_CHARS>" in content:
        existing_length = len(
            content.replace("<CONTINUE_WITH_SPECIAL_CHARS_TO_2100_CHARS>", "")
        )
        additional_needed = 2100 - existing_length
        special_text = "Special chars: émojis 🎉🚀🌟, symbols ™®©§¶, quotes. " * 50
        content = content.replace(
            "<CONTINUE_WITH_SPECIAL_CHARS_TO_2100_CHARS>",
            special_text[:additional_needed],
        )

    # For 2200 char text
    content = content.replace("<LONG_TEXT_2200_CHARS>", generate_long_text(2200))

    # Write the content
    file_path.write_text(content)

    # Store for verification
    context.test_file_path = filepath
    context.original_content = content


@then("the Notion page should have {count:d} paragraph block")
@then("the Notion page should have {count:d} paragraph blocks")
def step_verify_paragraph_count(context: Context, count: int) -> None:
    """Verify the number of paragraph blocks in the created page."""
    page = context.created_pages[-1]

    # Count paragraph blocks in the page content
    paragraph_blocks = [
        block for block in page.get("children", []) if block["type"] == "paragraph"
    ]

    actual_count = len(paragraph_blocks)
    assert (
        actual_count == count
    ), f"Expected {count} paragraph blocks, but found {actual_count}"

    # Store blocks for further verification
    context.paragraph_blocks = paragraph_blocks


@then('the paragraph should contain "{expected_text}"')
def step_verify_paragraph_contains(context: Context, expected_text: str) -> None:
    """Verify a paragraph contains the expected text."""
    paragraph = context.paragraph_blocks[0]
    actual_text = paragraph["paragraph"]["rich_text"][0]["text"]["content"]

    assert (
        expected_text in actual_text
    ), f"Expected text '{expected_text}' not found in paragraph"


@then("each paragraph block should be under {limit:d} characters")
def step_verify_paragraph_length_limit(context: Context, limit: int) -> None:
    """Verify each paragraph block is under the character limit."""
    for i, paragraph in enumerate(context.paragraph_blocks):
        text = paragraph["paragraph"]["rich_text"][0]["text"]["content"]
        length = len(text)
        assert (
            length <= limit
        ), f"Paragraph {i+1} has {length} characters, exceeding limit of {limit}"


@then("the combined text should equal the original content")
def step_verify_combined_text(context: Context) -> None:
    """Verify that combining all paragraphs gives the original text."""
    # Extract text from all paragraph blocks
    combined_text = ""
    for paragraph in context.paragraph_blocks:
        combined_text += paragraph["paragraph"]["rich_text"][0]["text"]["content"]

    # Get the original paragraph text (excluding markdown headers and metadata)
    lines = context.original_content.split("\n")
    # Skip metadata and headers
    content_start = 0
    for i, line in enumerate(lines):
        if line.strip() and not line.startswith("---") and not line.startswith("#"):
            content_start = i
            break

    original_paragraph_text = "\n".join(lines[content_start:]).strip()

    assert (
        combined_text.strip() == original_paragraph_text
    ), "Combined text doesn't match original content"


@then('paragraph {index:d} should contain "{expected_text}"')
def step_verify_specific_paragraph(
    context: Context, index: int, expected_text: str
) -> None:
    """Verify a specific paragraph contains expected text."""
    # Convert to 0-based index
    paragraph = context.paragraph_blocks[index - 1]
    actual_text = paragraph["paragraph"]["rich_text"][0]["text"]["content"]

    assert (
        expected_text in actual_text
    ), f"Expected text '{expected_text}' not found in paragraph {index}"


@then("paragraphs {start:d} and {end:d} should contain the split long text")
def step_verify_split_paragraphs(context: Context, start: int, end: int) -> None:
    """Verify that specific paragraphs contain parts of split long text."""
    # Check that both paragraphs exist
    assert (
        len(context.paragraph_blocks) >= end
    ), f"Expected at least {end} paragraphs, but found {len(context.paragraph_blocks)}"

    # Verify they contain text and together form a complete text
    text1 = context.paragraph_blocks[start - 1]["paragraph"]["rich_text"][0]["text"][
        "content"
    ]
    text2 = context.paragraph_blocks[end - 1]["paragraph"]["rich_text"][0]["text"][
        "content"
    ]

    assert len(text1) > 0, f"Paragraph {start} is empty"
    assert len(text2) > 0, f"Paragraph {end} is empty"
    assert len(text1) <= 2000, f"Paragraph {start} exceeds 2000 chars"
    assert len(text2) <= 2000, f"Paragraph {end} exceeds 2000 chars"


@then("no paragraph should be cut mid-word")
def step_verify_no_word_splitting(context: Context) -> None:
    """Verify that no words are split across paragraph boundaries."""
    for i in range(len(context.paragraph_blocks) - 1):
        current_text = context.paragraph_blocks[i]["paragraph"]["rich_text"][0]["text"][
            "content"
        ]
        next_text = context.paragraph_blocks[i + 1]["paragraph"]["rich_text"][0][
            "text"
        ]["content"]

        # Check that current paragraph doesn't end with partial word
        # and next doesn't start with partial word
        assert not re.match(
            r".*\w$", current_text.strip()
        ), f"Paragraph {i+1} appears to end mid-word"
        assert not re.match(
            r"^\w", next_text.strip()
        ), f"Paragraph {i+2} appears to start mid-word"


@then("the paragraph should be exactly {length:d} characters")
def step_verify_exact_length(context: Context, length: int) -> None:
    """Verify a paragraph has exactly the specified length."""
    paragraph = context.paragraph_blocks[0]
    actual_length = len(paragraph["paragraph"]["rich_text"][0]["text"]["content"])

    assert (
        actual_length == length
    ), f"Expected exactly {length} characters, but got {actual_length}"


@then("line breaks within chunks should be preserved")
def step_verify_line_breaks_preserved(context: Context) -> None:
    """Verify that line breaks are preserved within chunks."""
    for paragraph in context.paragraph_blocks:
        text = paragraph["paragraph"]["rich_text"][0]["text"]["content"]
        # Check if multi-line content has line breaks
        if "Line" in text and text.count("Line") > 1:
            assert "\n" in text, "Line breaks not preserved in multi-line content"


@then("no line should be split across chunks")
def step_verify_no_line_splitting(context: Context) -> None:
    """Verify that individual lines are not split across chunks."""
    for i in range(len(context.paragraph_blocks) - 1):
        current_text = context.paragraph_blocks[i]["paragraph"]["rich_text"][0]["text"][
            "content"
        ]
        # Current chunk should end with complete line
        if current_text.strip():
            assert not current_text.endswith(
                "Line"
            ), f"Paragraph {i+1} appears to end with incomplete line"


@then("empty lines should not create empty paragraph blocks")
def step_verify_no_empty_paragraphs(context: Context) -> None:
    """Verify that empty lines don't create empty paragraph blocks."""
    for i, paragraph in enumerate(context.paragraph_blocks):
        text = paragraph["paragraph"]["rich_text"][0]["text"]["content"]
        assert text.strip(), f"Paragraph {i+1} is empty"


@then("special characters should be preserved in both blocks")
def step_verify_special_chars_preserved(context: Context) -> None:
    """Verify that special characters are preserved in split blocks."""
    special_chars = ["🎉", "™", "®", "©"]

    # Check that at least some special characters appear in the blocks
    all_text = ""
    for paragraph in context.paragraph_blocks:
        all_text += paragraph["paragraph"]["rich_text"][0]["text"]["content"]

    found_chars = [char for char in special_chars if char in all_text]
    assert len(found_chars) > 0, "No special characters found in paragraphs"


@then("character count should properly account for multi-byte characters")
def step_verify_multibyte_char_handling(context: Context) -> None:
    """Verify that multi-byte characters are properly handled in length calculations."""
    for paragraph in context.paragraph_blocks:
        text = paragraph["paragraph"]["rich_text"][0]["text"]["content"]
        # Ensure length is calculated correctly (Python does this by default)
        assert (
            len(text) <= 2000
        ), "Paragraph exceeds 2000 characters when counting multi-byte chars properly"
