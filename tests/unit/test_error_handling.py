"""Unit tests for error handling module."""

import sys
import unittest
from unittest.mock import patch

from obsidian_to_notion.utils.error_handling import (
    ConfigError,
    MigrationError,
    NotionAPIError,
    ParseError,
    retry_on_api_error,
    safe_file_operation,
    setup_error_handling,
)


class TestExceptions(unittest.TestCase):
    """Test custom exception classes."""

    def test_migration_error(self):
        """Test MigrationError exception."""
        error = MigrationError("Test error")
        self.assertIsInstance(error, Exception)
        self.assertEqual(str(error), "Test error")

    def test_config_error(self):
        """Test ConfigError exception."""
        error = ConfigError("Invalid config")
        self.assertIsInstance(error, MigrationError)
        self.assertEqual(str(error), "Invalid config")

    def test_parse_error(self):
        """Test ParseError exception."""
        error = ParseError("Parse failed")
        self.assertIsInstance(error, MigrationError)
        self.assertEqual(str(error), "Parse failed")

    def test_notion_api_error(self):
        """Test NotionAPIError exception."""
        error = NotionAPIError("API failed")
        self.assertIsInstance(error, MigrationError)
        self.assertEqual(str(error), "API failed")


class TestSetupErrorHandling(unittest.TestCase):
    """Test setup_error_handling function."""

    def setUp(self):
        """Save original excepthook."""
        self.original_excepthook = sys.excepthook

    def tearDown(self):
        """Restore original excepthook."""
        sys.excepthook = self.original_excepthook

    def test_setup_error_handling(self):
        """Test setting up error handling."""
        setup_error_handling()
        # Check that excepthook was replaced
        self.assertNotEqual(sys.excepthook, self.original_excepthook)

    @patch("logging.error")
    def test_exception_handler(self, mock_log_error):
        """Test custom exception handler."""
        setup_error_handling()

        # Test the exception handler
        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = sys.exc_info()
            sys.excepthook(*exc_info)

        # Verify logging was called
        mock_log_error.assert_called_once()
        self.assertIn("Uncaught exception", mock_log_error.call_args[0][0])


class TestSafeFileOperation(unittest.TestCase):
    """Test safe_file_operation decorator."""

    def test_successful_operation(self):
        """Test decorator with successful operation."""

        @safe_file_operation
        def read_file(path):
            return f"Content of {path}"

        result = read_file("/test/file.txt")
        self.assertEqual(result, "Content of /test/file.txt")

    def test_file_not_found(self):
        """Test decorator with FileNotFoundError."""

        @safe_file_operation
        def read_file(path):
            raise FileNotFoundError("File not found")

        # FileNotFoundError is overridden in the module
        from obsidian_to_notion.utils.error_handling import (
            FileNotFoundError as CustomFileNotFoundError,
        )

        with self.assertRaises(CustomFileNotFoundError) as cm:
            read_file("/test/file.txt")
        self.assertIn("File not found", str(cm.exception))

    def test_permission_error(self):
        """Test decorator with PermissionError."""

        @safe_file_operation
        def read_file(path):
            raise PermissionError("Access denied")

        with self.assertRaises(MigrationError) as cm:
            read_file("/test/file.txt")
        self.assertIn("Permission denied", str(cm.exception))

    def test_io_error(self):
        """Test decorator with IOError."""

        @safe_file_operation
        def read_file(path):
            raise OSError("IO error")

        with self.assertRaises(MigrationError) as cm:
            read_file("/test/file.txt")
        self.assertIn("File operation failed", str(cm.exception))

    def test_other_exception(self):
        """Test decorator with other exceptions."""

        @safe_file_operation
        def read_file(path):
            raise ValueError("Other error")

        # Other exceptions should be wrapped in MigrationError
        with self.assertRaises(MigrationError) as cm:
            read_file("/test/file.txt")
        self.assertIn("File operation failed", str(cm.exception))

    def test_decorator_preserves_function_signature(self):
        """Test that decorator preserves function signature."""

        @safe_file_operation
        def read_file(path, mode="r"):
            return f"Reading {path} in {mode} mode"

        result = read_file("/test/file.txt", mode="rb")
        self.assertEqual(result, "Reading /test/file.txt in rb mode")


class TestRetryOnApiError(unittest.TestCase):
    """Test retry_on_api_error decorator."""

    def test_successful_operation(self):
        """Test decorator with successful operation."""

        @retry_on_api_error(max_retries=3)
        def api_call():
            return {"status": "success"}

        result = api_call()
        self.assertEqual(result, {"status": "success"})

    def test_retry_then_success(self):
        """Test decorator retries and then succeeds."""
        call_count = 0

        @retry_on_api_error(max_retries=3)
        def api_call():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NotionAPIError("Rate limited")
            return {"status": "success"}

        result = api_call()
        self.assertEqual(result, {"status": "success"})
        self.assertEqual(call_count, 3)

    def test_retry_max_retries(self):
        """Test decorator gives up after max attempts."""

        @retry_on_api_error(max_retries=2)
        def api_call():
            raise NotionAPIError("Rate limited")

        with self.assertRaises(NotionAPIError):
            api_call()

    def test_non_retryable_error(self):
        """Test decorator doesn't retry non-API errors."""
        call_count = 0

        @retry_on_api_error(max_retries=3)
        def api_call():
            nonlocal call_count
            call_count += 1
            raise ValueError("Other error")

        with self.assertRaises(ValueError):
            api_call()
        self.assertEqual(call_count, 1)  # Should not retry

    def test_decorator_with_arguments(self):
        """Test decorator works with function arguments."""

        @retry_on_api_error(max_retries=2)
        def api_call(page_id, data):
            return {"page_id": page_id, "data": data}

        result = api_call("test-id", {"title": "Test"})
        self.assertEqual(result["page_id"], "test-id")
        self.assertEqual(result["data"], {"title": "Test"})

    def test_error_logging(self):
        """Test that errors are logged."""
        with patch("obsidian_to_notion.utils.error_handling.logger") as mock_logger:

            @retry_on_api_error(max_retries=2)
            def api_call():
                raise NotionAPIError("API failed")

            with self.assertRaises(NotionAPIError):
                api_call()

            # Should log warning for first retry and error for final failure
            self.assertEqual(mock_logger.warning.call_count, 1)
            self.assertEqual(mock_logger.error.call_count, 1)


if __name__ == "__main__":
    unittest.main()
