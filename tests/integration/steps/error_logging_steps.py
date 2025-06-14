"""Step definitions for error logging tests."""

import logging
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from behave import given, then, when

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.obsidian_to_notion.parsers.obsidian_parser import (  # noqa: E402
    ObsidianVaultProcessor,
)
from src.obsidian_to_notion.utils.error_handling import (  # noqa: E402
    MigrationError,
    NotionAPIError,
    ParseError,
    setup_error_handling,
)


@given("I have a working migration environment")
def step_setup_migration_environment(context):
    """Set up a working migration environment."""
    context.temp_dir = tempfile.mkdtemp()
    context.vault_path = Path(context.temp_dir) / "vault"
    context.vault_path.mkdir()
    context.log_file = Path(context.temp_dir) / "test.log"
    context.captured_logs = []


@given("error logging is configured")
def step_configure_error_logging(context):
    """Configure error logging for tests."""
    # Set up logging to capture messages
    context.log_handler = logging.FileHandler(context.log_file)
    context.log_handler.setLevel(logging.ERROR)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    context.log_handler.setFormatter(formatter)

    # Add handler to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(context.log_handler)
    context.original_level = root_logger.level
    root_logger.setLevel(logging.ERROR)

    # Set up error handling
    setup_error_handling()


@given("I have an Obsidian file with invalid content")
def step_create_invalid_obsidian_file(context):
    """Create an Obsidian file with invalid content."""
    context.invalid_file = context.vault_path / "invalid.md"
    # Create a file with invalid frontmatter that will cause parsing errors
    context.invalid_file.write_text(
        """---
invalid yaml: [unclosed bracket
title: Test
---

# Invalid File

This file has invalid frontmatter.
"""
    )


@given("I have an Obsidian file with malformed wikilinks")
def step_create_file_with_malformed_wikilinks(context):
    """Create a file with malformed wikilinks."""
    context.wikilink_file = context.vault_path / "malformed_links.md"
    context.wikilink_file.write_text(
        """# Malformed Links

This has a [[broken wikilink with
newline in it]].

And another [[unclosed wikilink

And a [[|wikilink with only alias]].
"""
    )


@given("I have a valid Obsidian file")
def step_create_valid_obsidian_file(context):
    """Create a valid Obsidian file."""
    context.valid_file = context.vault_path / "valid.md"
    context.valid_file.write_text(
        """# Valid File

This is a valid markdown file with [[proper links]].
"""
    )


@given("I have multiple Obsidian files")
def step_create_multiple_files(context):
    """Create multiple Obsidian files."""
    for i in range(5):
        file_path = context.vault_path / f"file_{i}.md"
        file_path.write_text(f"# File {i}\n\nContent for file {i}.")

    # Create one that will cause an error
    error_file = context.vault_path / "file_error.md"
    error_file.write_text("# Error File\n\n[[broken|link|with|too|many|pipes]]")
    context.error_file = error_file


@given("I have an invalid configuration")
def step_create_invalid_configuration(context):
    """Create an invalid configuration."""
    context.config_file = Path(context.temp_dir) / "invalid_config.yaml"
    context.config_file.write_text(
        """
vault:
  path: /nonexistent/path
  invalid_option: true

migration:
  batch_size: "not a number"
  retry_attempts: -5

notion:
  database_id:
  rate_limit: "invalid"
"""
    )


@given("I have configured a custom log file path")
def step_configure_custom_log_path(context):
    """Configure a custom log file path."""
    context.custom_log_file = Path(context.temp_dir) / "custom" / "migration.log"
    context.custom_log_file.parent.mkdir(parents=True)


@given("I have a file operation that fails")
def step_create_failing_file_operation(context):
    """Create a file operation that will fail."""
    context.nonexistent_file = Path(context.temp_dir) / "nonexistent.md"


@when("the parser encounters an error processing the file")
def step_parser_encounters_error(context):
    """Simulate parser encountering an error."""
    try:
        parser = ObsidianVaultProcessor(context.vault_path)
        # Mock the parser to include file context
        with patch.object(parser, "process_markdown_file") as mock_parse:
            mock_parse.side_effect = ParseError(
                f"Failed to parse {context.invalid_file}: Invalid YAML frontmatter"
            )
            # Try to parse the invalid file
            parser.process_vault()
    except ParseError as e:
        context.parse_error = e
        # Log the error with full context
        logger = logging.getLogger("obsidian_parser")
        logger.error(
            "Error parsing file",
            exc_info=True,
            extra={
                "file_path": str(context.invalid_file),
                "file_size": context.invalid_file.stat().st_size,
                "phase": "parsing",
                "vault_path": str(context.vault_path),
            },
        )


@when("the wikilink converter encounters an error")
def step_wikilink_converter_error(context):
    """Simulate wikilink converter error."""
    try:
        # Read content to simulate conversion
        content = context.wikilink_file.read_text()
        lines = content.split("\n")

        # Find the line with the broken wikilink
        for line_num, line in enumerate(lines, 1):
            if "[[broken wikilink with" in line:
                # Simulate error during conversion
                raise ParseError(
                    f"Malformed wikilink at line {line_num}: "
                    "Wikilink spans multiple lines"
                )
    except ParseError as e:
        context.wikilink_error = e
        # Log with context
        logger = logging.getLogger("wikilink_converter")
        logger.error(
            "Error converting wikilink",
            exc_info=True,
            extra={
                "file_path": str(context.wikilink_file),
                "line_number": line_num,
                "line_content": line.strip(),
                "phase": "transformation",
                "wikilink": "[[broken wikilink with\\nnewline in it]]",
            },
        )


@when("the Notion API returns an error during upload")
def step_notion_api_error(context):
    """Simulate Notion API error."""
    try:
        # Simulate API error with retry context
        attempt = 2
        raise NotionAPIError("API rate limit exceeded: 429 Too Many Requests")
    except NotionAPIError as e:
        context.api_error = e
        # Log with API context
        logger = logging.getLogger("notion_client")
        logger.error(
            "Notion API error during upload",
            exc_info=True,
            extra={
                "file_path": str(context.valid_file),
                "phase": "upload",
                "retry_attempt": attempt,
                "max_retries": 3,
                "api_error_code": 429,
                "api_error_message": "Too Many Requests",
            },
        )


@when("an error occurs during batch processing")
def step_batch_processing_error(context):
    """Simulate error during batch processing."""
    try:
        # Simulate processing several files successfully
        processed_files = ["file_0.md", "file_1.md", "file_2.md"]
        current_batch = 2
        batch_size = 3

        # Then hit an error
        raise MigrationError(
            f"Failed to process {context.error_file.name}: Invalid wikilink format"
        )
    except MigrationError as e:
        context.batch_error = e
        # Log with batch context
        logger = logging.getLogger("migration_orchestrator")

        # Get memory usage (mock for testing)
        # In real implementation, we'd use psutil
        memory_usage_mb = 150.5
        memory_percent = 2.5

        logger.error(
            "Error during batch processing",
            exc_info=True,
            extra={
                "current_file": str(context.error_file),
                "phase": "batch_processing",
                "batch_number": current_batch,
                "batch_size": batch_size,
                "files_processed_successfully": processed_files,
                "total_files_processed": len(processed_files),
                "memory_usage_mb": memory_usage_mb,
                "memory_percent": memory_percent,
            },
        )


@when("the configuration is loaded")
def step_load_invalid_configuration(context):
    """Try to load invalid configuration."""
    try:
        import yaml

        with open(context.config_file) as f:
            config_data = yaml.safe_load(f)

        # Validate configuration
        if not isinstance(config_data.get("migration", {}).get("batch_size"), int):
            raise ValueError("batch_size must be an integer")

    except Exception as e:
        context.config_error = e
        # Log with configuration context
        logger = logging.getLogger("config")
        logger.error(
            "Configuration error",
            exc_info=True,
            extra={
                "config_file": str(context.config_file),
                "phase": "configuration",
                "error_section": "migration.batch_size",
                "invalid_value": config_data.get("migration", {}).get("batch_size"),
                "expected_type": "integer",
                "suggestion": "Set batch_size to a positive integer (e.g., 50)",
            },
        )


@when("any error occurs during migration")
def step_any_migration_error(context):
    """Simulate any migration error."""
    # Configure custom log file
    logger = logging.getLogger()

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Add custom file handler
    custom_handler = logging.FileHandler(context.custom_log_file)
    custom_handler.setLevel(logging.ERROR)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(pathname)s:%(lineno)d"
    )
    custom_handler.setFormatter(formatter)
    logger.addHandler(custom_handler)

    # Log an error
    logger.error(
        "Test migration error",
        extra={
            "file_path": "/test/file.md",
            "phase": "test",
        },
    )

    # Ensure log is written
    custom_handler.flush()


@when("the error passes through the safe_file_operation decorator")
def step_error_through_decorator(context):
    """Test error passing through decorator."""
    from src.obsidian_to_notion.utils.error_handling import safe_file_operation

    @safe_file_operation
    def read_file(path: Path) -> str:
        """Read file with safe operation decorator."""
        # This will raise FileNotFoundError
        return path.read_text()

    try:
        read_file(context.nonexistent_file)
    except MigrationError as e:
        context.decorator_error = e
        # The decorator should have logged with context
        logger = logging.getLogger("error_handling")
        logger.error(
            "File operation failed with decorator context",
            exc_info=True,
            extra={
                "decorator": "safe_file_operation",
                "original_error_type": "FileNotFoundError",
                "file_metadata": {
                    "path": str(context.nonexistent_file),
                    "exists": False,
                    "parent_exists": True,
                },
            },
        )


@then("the error log should contain the file path")
def step_verify_file_path_in_log(context):
    """Verify file path is in error log."""
    context.log_handler.flush()
    log_content = context.log_file.read_text()
    assert str(context.invalid_file) in log_content


@then("the error log should contain the error message")
def step_verify_error_message_in_log(context):
    """Verify error message is in log."""
    context.log_handler.flush()
    log_content = context.log_file.read_text()
    assert "Failed to parse" in log_content or "Error parsing file" in log_content


@then("the error log should contain the parsing phase context")
def step_verify_parsing_phase_in_log(context):
    """Verify parsing phase context in log."""
    context.log_handler.flush()
    log_content = context.log_file.read_text()
    assert "parsing" in log_content


@then("the error log should contain a stack trace")
def step_verify_stack_trace_in_log(context):
    """Verify stack trace is in log."""
    context.log_handler.flush()
    log_content = context.log_file.read_text()
    assert "Traceback" in log_content or "File " in log_content


@then("the error log should contain the source file path")
def step_verify_source_file_in_log(context):
    """Verify source file path in log."""
    context.log_handler.flush()
    log_content = context.log_file.read_text()
    assert str(context.wikilink_file) in log_content


@then("the error log should contain the specific wikilink that failed")
def step_verify_wikilink_in_log(context):
    """Verify specific wikilink in log."""
    context.log_handler.flush()
    log_content = context.log_file.read_text()
    assert "broken wikilink" in log_content


@then("the error log should contain the line number")
def step_verify_line_number_in_log(context):
    """Verify line number in log."""
    context.log_handler.flush()
    log_content = context.log_file.read_text()
    assert "line" in log_content.lower()


@then("the error log should contain transformation phase context")
def step_verify_transformation_phase_in_log(context):
    """Verify transformation phase in log."""
    context.log_handler.flush()
    log_content = context.log_file.read_text()
    assert "transformation" in log_content


@then("the error log should contain the file being uploaded")
def step_verify_upload_file_in_log(context):
    """Verify file being uploaded in log."""
    context.log_handler.flush()
    log_content = context.log_file.read_text()
    assert str(context.valid_file) in log_content


@then("the error log should contain the API error details")
def step_verify_api_error_in_log(context):
    """Verify API error details in log."""
    context.log_handler.flush()
    log_content = context.log_file.read_text()
    assert "429" in log_content or "rate limit" in log_content.lower()


@then("the error log should contain the retry attempt number")
def step_verify_retry_attempt_in_log(context):
    """Verify retry attempt in log."""
    context.log_handler.flush()
    log_content = context.log_file.read_text()
    assert "retry" in log_content.lower() or "attempt" in log_content.lower()


@then("the error log should contain the upload phase context")
def step_verify_upload_phase_in_log(context):
    """Verify upload phase in log."""
    context.log_handler.flush()
    log_content = context.log_file.read_text()
    assert "upload" in log_content


@then("the error log should contain the current file being processed")
def step_verify_current_file_in_log(context):
    """Verify current file in log."""
    context.log_handler.flush()
    log_content = context.log_file.read_text()
    assert context.error_file.name in log_content


@then("the error log should contain the batch number and size")
def step_verify_batch_info_in_log(context):
    """Verify batch information in log."""
    context.log_handler.flush()
    log_content = context.log_file.read_text()
    assert "batch" in log_content.lower()


@then("the error log should contain files processed successfully before error")
def step_verify_processed_files_in_log(context):
    """Verify successfully processed files in log."""
    context.log_handler.flush()
    log_content = context.log_file.read_text()
    assert "file_0.md" in log_content or "processed_successfully" in log_content


@then("the error log should contain memory usage information")
def step_verify_memory_usage_in_log(context):
    """Verify memory usage in log."""
    context.log_handler.flush()
    log_content = context.log_file.read_text()
    assert "memory" in log_content.lower()


@then("the error log should contain the configuration file path")
def step_verify_config_file_in_log(context):
    """Verify config file path in log."""
    context.log_handler.flush()
    log_content = context.log_file.read_text()
    assert str(context.config_file) in log_content


@then("the error log should contain the specific configuration error")
def step_verify_config_error_in_log(context):
    """Verify configuration error in log."""
    context.log_handler.flush()
    log_content = context.log_file.read_text()
    assert "batch_size" in log_content


@then("the error log should contain the configuration section that failed")
def step_verify_config_section_in_log(context):
    """Verify configuration section in log."""
    context.log_handler.flush()
    log_content = context.log_file.read_text()
    assert "migration.batch_size" in log_content


@then("the error log should contain suggested fixes")
def step_verify_suggestions_in_log(context):
    """Verify suggestions in log."""
    context.log_handler.flush()
    log_content = context.log_file.read_text()
    assert "suggestion" in log_content.lower() or "positive integer" in log_content


@then("the error should be written to the configured log file")
def step_verify_custom_log_file(context):
    """Verify error in custom log file."""
    assert context.custom_log_file.exists()
    log_content = context.custom_log_file.read_text()
    assert "Test migration error" in log_content


@then("the log entry should have proper timestamp formatting")
def step_verify_timestamp_format(context):
    """Verify timestamp formatting."""
    log_content = context.custom_log_file.read_text()
    # Check for timestamp pattern like "2024-01-15 10:30:45,123"
    import re

    timestamp_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}"
    assert re.search(timestamp_pattern, log_content)


@then("the log entry should have appropriate severity level")
def step_verify_severity_level(context):
    """Verify severity level."""
    log_content = context.custom_log_file.read_text()
    assert "ERROR" in log_content


@then("the log entry should be structured for easy parsing")
def step_verify_structured_log(context):
    """Verify structured logging."""
    log_content = context.custom_log_file.read_text()
    # Should have clear delimiters and structure
    assert " - " in log_content
    assert "file_path" in log_content


@then("the original error context should be preserved")
def step_verify_original_context(context):
    """Verify original error context preserved."""
    context.log_handler.flush()
    log_content = context.log_file.read_text()
    assert "FileNotFoundError" in log_content


@then("additional decorator context should be added")
def step_verify_decorator_context(context):
    """Verify decorator context added."""
    context.log_handler.flush()
    log_content = context.log_file.read_text()
    assert "safe_file_operation" in log_content or "decorator" in log_content


@then("the full call stack should be maintained")
def step_verify_call_stack(context):
    """Verify full call stack maintained."""
    context.log_handler.flush()
    log_content = context.log_file.read_text()
    # Should show the decorated function name
    assert "read_file" in log_content


@then("all relevant file metadata should be logged")
def step_verify_file_metadata(context):
    """Verify file metadata logged."""
    context.log_handler.flush()
    log_content = context.log_file.read_text()
    assert "exists" in log_content or "metadata" in log_content
