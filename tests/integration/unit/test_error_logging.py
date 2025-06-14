"""Unit tests for enhanced error logging functionality."""

import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.obsidian_to_notion.utils.error_handling import (
    ConfigError,
    FileNotFoundError,
    MigrationError,
    NotionAPIError,
    ParseError,
    log_error_with_context,
    retry_on_api_error,
    safe_file_operation,
    setup_error_handling,
)


class TestErrorLogging(unittest.TestCase):
    """Test cases for enhanced error logging."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = Path(self.temp_dir) / "test.log"

        # Set up test logger
        self.logger = logging.getLogger("test_logger")
        self.logger.handlers = []
        self.handler = logging.FileHandler(self.log_file)
        self.handler.setLevel(logging.ERROR)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        self.handler.setFormatter(formatter)
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.ERROR)

    def tearDown(self):
        """Clean up test fixtures."""
        # Close and remove handler
        self.handler.close()
        self.logger.removeHandler(self.handler)

        # Clean up temp directory
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_log_error_with_context(self):
        """Test logging error with full context."""
        error = ParseError("Failed to parse file")
        context = {
            "file_path": "/path/to/file.md",
            "line_number": 42,
            "phase": "parsing",
            "vault_path": "/path/to/vault",
        }

        log_error_with_context(self.logger, error, context)

        # Check log content
        self.handler.flush()
        log_content = self.log_file.read_text()

        # Verify all context information is logged
        self.assertIn("Failed to parse file", log_content)
        self.assertIn("/path/to/file.md", log_content)
        self.assertIn("42", log_content)
        self.assertIn("parsing", log_content)
        self.assertIn("/path/to/vault", log_content)

    def test_safe_file_operation_preserves_context(self):
        """Test that safe_file_operation preserves error context."""

        @safe_file_operation
        def read_test_file(path: Path) -> str:
            """Test function that reads a file."""
            return path.read_text()

        nonexistent = Path(self.temp_dir) / "nonexistent.md"

        with self.assertRaises(FileNotFoundError) as cm:
            read_test_file(nonexistent)

        # The error should contain the original path
        self.assertIn(str(nonexistent), str(cm.exception))

    def test_safe_file_operation_adds_context(self):
        """Test that safe_file_operation adds additional context."""

        @safe_file_operation
        def write_test_file(path: Path, content: str) -> None:
            """Test function that writes a file."""
            # Create a read-only directory
            path.parent.mkdir(mode=0o444, exist_ok=True)
            path.write_text(content)

        readonly_file = Path(self.temp_dir) / "readonly" / "test.md"

        with self.assertRaises(MigrationError) as cm:
            write_test_file(readonly_file, "test content")

        # Should wrap permission error
        self.assertIn("Permission denied", str(cm.exception))

    def test_retry_on_api_error_logs_attempts(self):
        """Test that retry decorator logs each attempt."""
        attempt_count = 0

        @retry_on_api_error(max_retries=3)
        def failing_api_call():
            """Test function that fails with API error."""
            nonlocal attempt_count
            attempt_count += 1
            raise NotionAPIError(f"API error on attempt {attempt_count}")

        # Capture logs
        with self.assertLogs("error_handling", level="WARNING") as cm:
            with self.assertRaises(NotionAPIError):
                failing_api_call()

        # Should have 2 warning logs (attempts 1 and 2)
        warning_logs = [log for log in cm.output if "WARNING" in log]
        self.assertEqual(len(warning_logs), 2)

        # Check that attempts are logged
        self.assertTrue(any("attempt 1/3" in log for log in warning_logs))
        self.assertTrue(any("attempt 2/3" in log for log in warning_logs))

    def test_error_logging_with_file_metadata(self):
        """Test error logging includes file metadata."""
        test_file = Path(self.temp_dir) / "test.md"
        test_file.write_text("# Test\n\nContent")

        error = ParseError("Invalid frontmatter")
        context = {
            "file_path": str(test_file),
            "file_size": test_file.stat().st_size,
            "file_modified": test_file.stat().st_mtime,
            "phase": "parsing",
        }

        log_error_with_context(self.logger, error, context)

        self.handler.flush()
        log_content = self.log_file.read_text()

        # Should include file metadata
        self.assertIn(str(test_file), log_content)
        self.assertIn("parsing", log_content)

    def test_error_logging_with_wikilink_context(self):
        """Test error logging for wikilink conversion errors."""
        error = ParseError("Malformed wikilink")
        context = {
            "file_path": "/vault/notes/test.md",
            "line_number": 10,
            "line_content": "This has [[broken|link|syntax]]",
            "wikilink": "[[broken|link|syntax]]",
            "phase": "wikilink_conversion",
        }

        log_error_with_context(self.logger, error, context)

        self.handler.flush()
        log_content = self.log_file.read_text()

        # Should include wikilink details
        self.assertIn("line_number", log_content)
        self.assertIn("10", log_content)
        self.assertIn("broken|link|syntax", log_content)
        self.assertIn("wikilink_conversion", log_content)

    def test_error_logging_with_api_context(self):
        """Test error logging for Notion API errors."""
        error = NotionAPIError("Rate limit exceeded")
        context = {
            "file_path": "/vault/notes/upload.md",
            "phase": "upload",
            "retry_attempt": 3,
            "max_retries": 3,
            "api_error_code": 429,
            "api_endpoint": "/v1/pages",
            "request_id": "req_123456",
        }

        log_error_with_context(self.logger, error, context)

        self.handler.flush()
        log_content = self.log_file.read_text()

        # Should include API details
        self.assertIn("429", log_content)
        self.assertIn("retry_attempt", log_content)
        self.assertIn("upload", log_content)
        self.assertIn("req_123456", log_content)

    def test_error_logging_with_batch_context(self):
        """Test error logging during batch processing."""
        error = MigrationError("Batch processing failed")
        context = {
            "current_file": "/vault/file_5.md",
            "batch_number": 2,
            "batch_size": 10,
            "files_processed": 15,
            "files_failed": 1,
            "phase": "batch_processing",
            "memory_usage_mb": 256.7,
        }

        log_error_with_context(self.logger, error, context)

        self.handler.flush()
        log_content = self.log_file.read_text()

        # Should include batch processing details
        self.assertIn("batch_number", log_content)
        self.assertIn("files_processed", log_content)
        self.assertIn("memory_usage_mb", log_content)

    def test_error_logging_with_config_context(self):
        """Test error logging for configuration errors."""
        error = ConfigError("Invalid configuration value")
        context = {
            "config_file": "/path/to/config.yaml",
            "config_section": "migration.batch_size",
            "invalid_value": "not_a_number",
            "expected_type": "integer",
            "phase": "configuration",
            "suggestion": "Use a positive integer value",
        }

        log_error_with_context(self.logger, error, context)

        self.handler.flush()
        log_content = self.log_file.read_text()

        # Should include configuration details
        self.assertIn("config.yaml", log_content)
        self.assertIn("batch_size", log_content)
        self.assertIn("not_a_number", log_content)
        self.assertIn("suggestion", log_content)

    def test_setup_error_handling_catches_uncaught(self):
        """Test that setup_error_handling catches uncaught exceptions."""
        setup_error_handling()

        # Mock the logger to capture calls
        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            # Simulate an uncaught exception
            import sys

            try:
                raise RuntimeError("Uncaught test error")
            except RuntimeError:
                exc_info = sys.exc_info()
                sys.excepthook(*exc_info)

            # Should have logged the error
            mock_logger.error.assert_called()
            call_args = mock_logger.error.call_args
            self.assertIn("Uncaught exception", call_args[0][0])

    def test_structured_error_logging(self):
        """Test that errors are logged in structured format."""
        error = MigrationError("Test structured logging")
        context = {
            "file_path": "/test/file.md",
            "phase": "test",
            "metadata": {
                "size": 1024,
                "lines": 50,
            },
        }

        # Log with structured format
        import json

        structured_context = json.dumps(context, indent=2)
        self.logger.error(f"{error}\nContext:\n{structured_context}", exc_info=True)

        self.handler.flush()
        log_content = self.log_file.read_text()

        # Should be parseable as structured data
        self.assertIn('"file_path":', log_content)
        self.assertIn('"phase":', log_content)
        self.assertIn('"metadata":', log_content)

    def test_error_chain_preservation(self):
        """Test that error chains are preserved through decorators."""
        original_error = FileNotFoundError("Original file error")

        @safe_file_operation
        def operation_that_fails():
            """Operation that raises the original error."""
            raise original_error

        with self.assertRaises(MigrationError) as cm:
            operation_that_fails()

        # Should preserve the original error in the chain
        self.assertIs(cm.exception.__cause__, original_error)
        self.assertEqual(str(cm.exception.__cause__), "Original file error")

    def test_concurrent_error_logging(self):
        """Test that concurrent errors are logged correctly."""
        import concurrent.futures
        import time

        def failing_operation(file_num: int):
            """Operation that fails with context."""
            time.sleep(0.01)  # Small delay to ensure concurrency
            error = MigrationError(f"Failed processing file_{file_num}.md")
            log_error_with_context(
                self.logger,
                error,
                {"file_path": f"/vault/file_{file_num}.md", "phase": "concurrent"},
            )
            raise error

        # Run multiple operations concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(failing_operation, i) for i in range(5)]

            # Wait for all to complete (they will all fail)
            for future in futures:
                try:
                    future.result()
                except MigrationError:
                    pass

        self.handler.flush()
        log_content = self.log_file.read_text()

        # All errors should be logged
        for i in range(5):
            self.assertIn(f"file_{i}.md", log_content)


if __name__ == "__main__":
    unittest.main()
