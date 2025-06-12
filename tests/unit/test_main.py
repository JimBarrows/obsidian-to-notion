"""Unit tests for main module."""

import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from obsidian_to_notion.main import main, setup_logging


class TestSetupLogging(unittest.TestCase):
    """Test setup_logging function."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear existing handlers
        logging.root.handlers.clear()

    def test_setup_logging_default(self):
        """Test setup_logging with default settings."""
        from obsidian_to_notion.config import AppConfig, LoggingConfig

        config = MagicMock(spec=AppConfig)
        config.logging = LoggingConfig()

        setup_logging(config, verbose=False)

        # Check root logger level
        self.assertEqual(logging.root.level, logging.INFO)
        # Check handlers were added
        self.assertEqual(len(logging.root.handlers), 2)  # console and file

    def test_setup_logging_verbose(self):
        """Test setup_logging with verbose mode."""
        from obsidian_to_notion.config import AppConfig, LoggingConfig

        config = MagicMock(spec=AppConfig)
        config.logging = LoggingConfig()

        setup_logging(config, verbose=True)

        # Check root logger level
        self.assertEqual(logging.root.level, logging.DEBUG)

    def test_setup_logging_custom_level(self):
        """Test setup_logging with custom log level."""
        from obsidian_to_notion.config import AppConfig, LoggingConfig

        config = MagicMock(spec=AppConfig)
        config.logging = LoggingConfig(level="WARNING")

        setup_logging(config, verbose=False)

        # Check root logger level
        self.assertEqual(logging.root.level, logging.WARNING)


class TestMain(unittest.TestCase):
    """Test main function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.vault_path = Path(self.temp_dir) / "vault"
        self.vault_path.mkdir()
        self.config_file = Path(self.temp_dir) / "config.yaml"

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def create_config_file(self):
        """Create a test config file."""
        config_data = {
            "vault": {"path": str(self.vault_path)},
        }
        with open(self.config_file, "w") as f:
            yaml.dump(config_data, f)

    @patch("obsidian_to_notion.main.setup_error_handling")
    @patch("obsidian_to_notion.main.AppConfig.load_from_file")
    @patch("obsidian_to_notion.main.setup_logging")
    @patch("sys.argv", ["obsidian-to-notion"])
    def test_main_success(
        self, mock_setup_logging, mock_load_config, mock_error_handler
    ):
        """Test successful main execution."""
        # Mock config
        mock_config = MagicMock()
        mock_config.vault.path = str(self.vault_path)
        mock_config.logging.progress_bar = True
        mock_config.migration.batch_size = 50
        mock_config.migration.parallel_workers = 3
        mock_config.validate.return_value = None
        mock_load_config.return_value = mock_config

        # Run main (currently doesn't exit)
        main()

        # Verify calls
        mock_error_handler.assert_called_once()
        mock_load_config.assert_called_once_with("config.yaml")
        mock_setup_logging.assert_called_once_with(mock_config, False)
        mock_config.validate.assert_called_once()

    @patch("obsidian_to_notion.main.setup_error_handling")
    @patch("obsidian_to_notion.main.AppConfig.load_from_file")
    @patch("sys.argv", ["obsidian-to-notion", "--config", "custom.yaml"])
    def test_main_custom_config(self, mock_load_config, mock_error_handler):
        """Test main with custom config file."""
        mock_config = MagicMock()
        mock_config.validate.return_value = None
        mock_load_config.return_value = mock_config

        main()

        mock_load_config.assert_called_once_with("custom.yaml")

    @patch("obsidian_to_notion.main.setup_error_handling")
    @patch("obsidian_to_notion.main.AppConfig.load_from_file")
    @patch("sys.argv", ["obsidian-to-notion", "--vault", "/custom/vault"])
    def test_main_vault_override(self, mock_load_config, mock_error_handler):
        """Test main with vault path override."""
        mock_config = MagicMock()
        mock_config.validate.return_value = None
        mock_load_config.return_value = mock_config

        main()

        # Verify vault path was overridden
        self.assertEqual(mock_config.vault.path, "/custom/vault")

    @patch("obsidian_to_notion.main.setup_error_handling")
    @patch("obsidian_to_notion.main.AppConfig.load_from_file")
    @patch("sys.argv", ["obsidian-to-notion", "--verbose"])
    def test_main_verbose(self, mock_load_config, mock_error_handler):
        """Test main with verbose flag."""
        mock_config = MagicMock()
        mock_config.validate.return_value = None
        mock_load_config.return_value = mock_config

        with patch("obsidian_to_notion.main.setup_logging") as mock_setup_logging:
            main()

            # Verify verbose was passed to setup_logging
            mock_setup_logging.assert_called_once_with(mock_config, True)

    @patch("obsidian_to_notion.main.setup_error_handling")
    @patch("obsidian_to_notion.main.AppConfig.load_from_file")
    @patch("sys.argv", ["obsidian-to-notion", "--dry-run"])
    def test_main_dry_run(self, mock_load_config, mock_error_handler):
        """Test main with dry-run flag."""
        mock_config = MagicMock()
        mock_config.validate.return_value = None
        mock_load_config.return_value = mock_config

        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            main()

            # Verify dry-run message was logged
            mock_logger.info.assert_any_call(
                "Running in dry-run mode - no changes will be made to Notion"
            )

    @patch("obsidian_to_notion.main.setup_error_handling")
    @patch("obsidian_to_notion.main.AppConfig.load_from_file")
    @patch("sys.argv", ["obsidian-to-notion"])
    def test_main_config_not_found(self, mock_load_config, mock_error_handler):
        """Test main when config file not found."""
        mock_load_config.side_effect = FileNotFoundError("Config not found")

        with self.assertRaises(SystemExit) as cm:
            main()

        self.assertEqual(cm.exception.code, 1)

    @patch("obsidian_to_notion.main.setup_error_handling")
    @patch("obsidian_to_notion.main.AppConfig.load_from_file")
    @patch("sys.argv", ["obsidian-to-notion"])
    def test_main_validation_error(self, mock_load_config, mock_error_handler):
        """Test main when config validation fails."""
        mock_config = MagicMock()
        mock_config.validate.side_effect = ValueError("Invalid config")
        mock_load_config.return_value = mock_config

        with self.assertRaises(SystemExit) as cm:
            main()

        self.assertEqual(cm.exception.code, 1)

    @patch("obsidian_to_notion.main.setup_error_handling")
    @patch("obsidian_to_notion.main.AppConfig.load_from_file")
    @patch("sys.argv", ["obsidian-to-notion"])
    def test_main_unexpected_error(self, mock_load_config, mock_error_handler):
        """Test main with unexpected error."""
        mock_load_config.side_effect = Exception("Unexpected error")

        with self.assertRaises(SystemExit) as cm:
            main()

        self.assertEqual(cm.exception.code, 1)

    @patch("obsidian_to_notion.main.setup_error_handling")
    @patch("obsidian_to_notion.main.AppConfig.load_from_file")
    @patch("obsidian_to_notion.main.ProgressReporter")
    @patch("sys.argv", ["obsidian-to-notion"])
    def test_main_no_progress_bar(
        self, mock_progress, mock_load_config, mock_error_handler
    ):
        """Test main without progress bar."""
        mock_config = MagicMock()
        mock_config.logging.progress_bar = False
        mock_config.validate.return_value = None
        mock_load_config.return_value = mock_config

        main()

        # Verify ProgressReporter was not instantiated
        mock_progress.assert_not_called()


if __name__ == "__main__":
    unittest.main()
