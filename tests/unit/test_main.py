"""Unit tests for main module and ObsidianToNotionMigrator."""

import logging
import os
import tempfile
import unittest
from unittest.mock import MagicMock, Mock, patch

import pytest
from obsidian_to_notion.config import AppConfig
from obsidian_to_notion.main import ObsidianToNotionMigrator, main, setup_logging
from obsidian_to_notion.utils.error_handling import MigrationError


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


class TestObsidianToNotionMigrator:
    """Test ObsidianToNotionMigrator class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup
        import shutil

        shutil.rmtree(temp_dir)

    @pytest.fixture
    def config(self, temp_dir):
        """Create test configuration."""
        vault_path = os.path.join(temp_dir, "vault")
        os.makedirs(vault_path, exist_ok=True)

        from obsidian_to_notion.config import (
            LoggingConfig,
            MigrationConfig,
            NotionConfig,
            VaultConfig,
        )

        config = AppConfig(
            vault=VaultConfig(path=vault_path),
            migration=MigrationConfig(),
            notion=NotionConfig(token="test-token", database_id="test-db-id"),
            logging=LoggingConfig(
                log_file=os.path.join(temp_dir, "test.log"), level="INFO"
            ),
        )
        return config

    @patch("obsidian_to_notion.main.WikilinkConverter")
    @patch("obsidian_to_notion.main.DeduplicationManager")
    @patch("obsidian_to_notion.main.NotionMigrationClient")
    @patch("obsidian_to_notion.main.ObsidianVaultProcessor")
    def test_init(
        self,
        mock_processor_class,
        mock_client_class,
        mock_dedup_class,
        mock_converter_class,
        config,
    ):
        """Test migrator initialization."""
        # Create migrator
        migrator = ObsidianToNotionMigrator(config)

        # Verify components were initialized
        mock_processor_class.assert_called_once_with(config.vault.path)
        mock_client_class.assert_called_once_with(
            config.notion.token, config.notion.rate_limit_requests_per_second
        )
        mock_converter_class.assert_called_once()
        mock_dedup_class.assert_called_once_with(
            migrator.notion_client, config.notion.database_id
        )

        # Verify logger was created
        assert migrator.logger is not None

    @patch("obsidian_to_notion.main.WikilinkConverter")
    @patch("obsidian_to_notion.main.DeduplicationManager")
    @patch("obsidian_to_notion.main.NotionMigrationClient")
    @patch("obsidian_to_notion.main.ObsidianVaultProcessor")
    def test_migrate_empty_vault(
        self,
        mock_processor_class,
        mock_client_class,
        mock_dedup_class,
        mock_converter_class,
        config,
    ):
        """Test migration with empty vault."""
        # Mock empty vault
        mock_processor = Mock()
        mock_processor.process_vault.return_value = {
            "markdown_files": [],
            "attachments": [],
            "wikilink_map": {},
        }
        mock_processor_class.return_value = mock_processor

        # Create and run migrator
        migrator = ObsidianToNotionMigrator(config)
        result = migrator.migrate()

        # Verify result
        assert result["status"] == "no_files"
        assert result["stats"] == {}
        mock_processor.process_vault.assert_called_once()

    @patch("obsidian_to_notion.main.WikilinkConverter")
    @patch("obsidian_to_notion.main.DeduplicationManager")
    @patch("obsidian_to_notion.main.NotionMigrationClient")
    @patch("obsidian_to_notion.main.ObsidianVaultProcessor")
    def test_migrate_success(
        self,
        mock_processor_class,
        mock_client_class,
        mock_dedup_class,
        mock_converter_class,
        config,
    ):
        """Test successful migration."""
        # Mock vault data
        mock_processor = Mock()
        mock_processor.process_vault.return_value = {
            "markdown_files": [
                {
                    "path": "/vault/note1.md",
                    "title": "Note 1",
                    "content": "Content 1",
                    "metadata": {},
                    "wikilinks": [],
                },
                {
                    "path": "/vault/note2.md",
                    "title": "Note 2",
                    "content": "Content 2 with [[Note 1]]",
                    "metadata": {"tags": "test"},
                    "wikilinks": [{"note_name": "Note 1"}],
                },
            ],
            "attachments": [],
            "wikilink_map": {"note 1": "/vault/note1.md"},
        }
        mock_processor.sanitize_for_notion.side_effect = lambda x: x
        mock_processor_class.return_value = mock_processor

        # Mock Notion client
        mock_client = Mock()
        mock_client.create_page.side_effect = [{"id": "page-1"}, {"id": "page-2"}]
        mock_client_class.return_value = mock_client

        # Mock wikilink converter
        mock_converter = Mock()
        mock_converter.convert_content.side_effect = lambda content, links: content
        mock_converter.get_broken_links_report.return_value = "No broken links found"
        mock_converter_class.return_value = mock_converter

        # Mock dedup manager
        mock_dedup = Mock()
        mock_dedup.should_skip_page.return_value = False
        mock_dedup_class.return_value = mock_dedup

        # Create and run migrator
        migrator = ObsidianToNotionMigrator(config)

        with patch("obsidian_to_notion.main.ProgressTracker"):
            result = migrator.migrate()

        # Verify result
        assert result["status"] == "completed"
        assert result["stats"]["successful"] == 2
        assert result["stats"]["failed"] == 0
        assert result["stats"]["skipped"] == 0
        assert "report" in result

        # Verify pages were created
        assert mock_client.create_page.call_count == 2

    @patch("obsidian_to_notion.main.WikilinkConverter")
    @patch("obsidian_to_notion.main.DeduplicationManager")
    @patch("obsidian_to_notion.main.NotionMigrationClient")
    @patch("obsidian_to_notion.main.ObsidianVaultProcessor")
    def test_migrate_with_duplicates(
        self,
        mock_processor_class,
        mock_client_class,
        mock_dedup_class,
        mock_converter_class,
        config,
    ):
        """Test migration with duplicate detection."""
        # Enable skip duplicates
        config.migration.skip_duplicates = True

        # Mock vault data
        mock_processor = Mock()
        mock_processor.process_vault.return_value = {
            "markdown_files": [
                {
                    "title": "Existing Note",
                    "content": "Content",
                    "metadata": {},
                    "wikilinks": [],
                },
                {
                    "title": "New Note",
                    "content": "Content",
                    "metadata": {},
                    "wikilinks": [],
                },
            ],
            "attachments": [],
            "wikilink_map": {},
        }
        mock_processor.sanitize_for_notion.side_effect = lambda x: x
        mock_processor_class.return_value = mock_processor

        # Mock dedup manager
        mock_dedup = Mock()
        mock_dedup.should_skip_page.side_effect = [
            True,
            False,
        ]  # Skip first, not second
        mock_dedup_class.return_value = mock_dedup

        # Mock Notion client
        mock_client = Mock()
        mock_client.create_page.return_value = {"id": "new-page"}
        mock_client_class.return_value = mock_client

        # Mock converter
        mock_converter = Mock()
        mock_converter.convert_content.side_effect = lambda content, links: content
        mock_converter.get_broken_links_report.return_value = "No broken links found"
        mock_converter_class.return_value = mock_converter

        # Create and run migrator
        migrator = ObsidianToNotionMigrator(config)

        with patch("obsidian_to_notion.main.ProgressTracker"):
            result = migrator.migrate()

        # Verify result
        assert result["stats"]["successful"] == 1
        assert result["stats"]["skipped"] == 1
        assert result["stats"]["failed"] == 0

        # Verify dedup was loaded
        mock_dedup.load_existing_pages.assert_called_once()

    @patch("obsidian_to_notion.main.WikilinkConverter")
    @patch("obsidian_to_notion.main.DeduplicationManager")
    @patch("obsidian_to_notion.main.NotionMigrationClient")
    @patch("obsidian_to_notion.main.ObsidianVaultProcessor")
    def test_migrate_dry_run(
        self,
        mock_processor_class,
        mock_client_class,
        mock_dedup_class,
        mock_converter_class,
        config,
    ):
        """Test dry-run migration."""
        # Mock vault data
        mock_processor = Mock()
        mock_processor.process_vault.return_value = {
            "markdown_files": [
                {
                    "title": "Note 1",
                    "content": "Content",
                    "metadata": {},
                    "wikilinks": [],
                },
                {
                    "title": "Note 2",
                    "content": "Content",
                    "metadata": {},
                    "wikilinks": [],
                },
            ],
            "attachments": [],
            "wikilink_map": {},
        }
        mock_processor_class.return_value = mock_processor

        # Mock dedup
        mock_dedup = Mock()
        mock_dedup.should_skip_page.return_value = False
        mock_dedup_class.return_value = mock_dedup

        # Create and run migrator in dry-run mode
        migrator = ObsidianToNotionMigrator(config)

        with patch("builtins.print") as mock_print:
            result = migrator.migrate(dry_run=True)

        # Verify result
        assert result["status"] == "completed"
        assert result["stats"]["successful"] == 2

        # Verify print was called with dry-run messages
        mock_print.assert_any_call("WOULD CREATE: Note 1")
        mock_print.assert_any_call("WOULD CREATE: Note 2")

        # Verify no actual pages were created
        migrator.notion_client.create_page.assert_not_called()

    @patch("obsidian_to_notion.main.WikilinkConverter")
    @patch("obsidian_to_notion.main.DeduplicationManager")
    @patch("obsidian_to_notion.main.NotionMigrationClient")
    @patch("obsidian_to_notion.main.ObsidianVaultProcessor")
    def test_migrate_with_errors(
        self,
        mock_processor_class,
        mock_client_class,
        mock_dedup_class,
        mock_converter_class,
        config,
    ):
        """Test migration with errors."""
        # Mock vault data
        mock_processor = Mock()
        mock_processor.process_vault.return_value = {
            "markdown_files": [
                {
                    "title": "Good Note",
                    "content": "Content",
                    "metadata": {},
                    "wikilinks": [],
                },
                {
                    "title": "Bad Note",
                    "content": "Content",
                    "metadata": {},
                    "wikilinks": [],
                },
            ],
            "attachments": [],
            "wikilink_map": {},
        }
        mock_processor.sanitize_for_notion.side_effect = lambda x: x
        mock_processor_class.return_value = mock_processor

        # Mock Notion client - fail on second page
        mock_client = Mock()
        mock_client.create_page.side_effect = [
            {"id": "good-page"},
            Exception("API Error"),
        ]
        mock_client_class.return_value = mock_client

        # Mock converter
        mock_converter = Mock()
        mock_converter.convert_content.side_effect = lambda content, links: content
        mock_converter.get_broken_links_report.return_value = "No broken links found"
        mock_converter_class.return_value = mock_converter

        # Mock dedup
        mock_dedup = Mock()
        mock_dedup.should_skip_page.return_value = False
        mock_dedup_class.return_value = mock_dedup

        # Create and run migrator
        migrator = ObsidianToNotionMigrator(config)

        with patch("obsidian_to_notion.main.ProgressTracker"):
            result = migrator.migrate()

        # Verify result
        assert result["stats"]["successful"] == 1
        assert result["stats"]["failed"] == 1
        assert len(result["stats"]["errors"]) == 1
        assert result["stats"]["errors"][0]["file"] == "Bad Note"

    def test_content_to_notion_blocks_empty(self, config):
        """Test converting empty content to Notion blocks."""
        with patch("obsidian_to_notion.main.ObsidianVaultProcessor"), patch(
            "obsidian_to_notion.main.NotionMigrationClient"
        ), patch("obsidian_to_notion.main.WikilinkConverter"), patch(
            "obsidian_to_notion.main.DeduplicationManager"
        ):

            migrator = ObsidianToNotionMigrator(config)
            blocks = migrator._content_to_notion_blocks("")

            assert blocks == []

    def test_content_to_notion_blocks_single_paragraph(self, config):
        """Test converting single paragraph to Notion blocks."""
        with patch("obsidian_to_notion.main.ObsidianVaultProcessor"), patch(
            "obsidian_to_notion.main.NotionMigrationClient"
        ), patch("obsidian_to_notion.main.WikilinkConverter"), patch(
            "obsidian_to_notion.main.DeduplicationManager"
        ):

            migrator = ObsidianToNotionMigrator(config)
            blocks = migrator._content_to_notion_blocks("This is a test paragraph.")

            assert len(blocks) == 1
            assert blocks[0]["type"] == "paragraph"
            assert (
                blocks[0]["paragraph"]["rich_text"][0]["text"]["content"]
                == "This is a test paragraph."
            )

    def test_content_to_notion_blocks_multiple_paragraphs(self, config):
        """Test converting multiple paragraphs to Notion blocks."""
        with patch("obsidian_to_notion.main.ObsidianVaultProcessor"), patch(
            "obsidian_to_notion.main.NotionMigrationClient"
        ), patch("obsidian_to_notion.main.WikilinkConverter"), patch(
            "obsidian_to_notion.main.DeduplicationManager"
        ):

            migrator = ObsidianToNotionMigrator(config)
            content = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
            blocks = migrator._content_to_notion_blocks(content)

            assert len(blocks) == 3
            assert all(block["type"] == "paragraph" for block in blocks)
            assert (
                blocks[0]["paragraph"]["rich_text"][0]["text"]["content"]
                == "First paragraph."
            )
            assert (
                blocks[1]["paragraph"]["rich_text"][0]["text"]["content"]
                == "Second paragraph."
            )
            assert (
                blocks[2]["paragraph"]["rich_text"][0]["text"]["content"]
                == "Third paragraph."
            )

    @patch("obsidian_to_notion.main.WikilinkConverter")
    @patch("obsidian_to_notion.main.DeduplicationManager")
    @patch("obsidian_to_notion.main.NotionMigrationClient")
    @patch("obsidian_to_notion.main.ObsidianVaultProcessor")
    def test_migrate_exception_handling(
        self,
        mock_processor_class,
        mock_client_class,
        mock_dedup_class,
        mock_converter_class,
        config,
    ):
        """Test exception handling during migration."""
        # Mock processor to raise exception
        mock_processor = Mock()
        mock_processor.process_vault.side_effect = Exception("Vault processing failed")
        mock_processor_class.return_value = mock_processor

        # Create and run migrator
        migrator = ObsidianToNotionMigrator(config)

        with pytest.raises(MigrationError) as exc_info:
            migrator.migrate()

        assert "Migration failed: Vault processing failed" in str(exc_info.value)


class TestMain(unittest.TestCase):
    """Test main function."""

    @patch("sys.argv", ["obsidian-to-notion"])
    @patch("obsidian_to_notion.main.ObsidianToNotionMigrator")
    @patch("obsidian_to_notion.main.AppConfig.load_from_file")
    def test_main_success(self, mock_load_config, mock_migrator_class):
        """Test successful main execution."""
        # Mock config
        mock_config = Mock()
        mock_config.notion.token = "test-token"
        mock_config.notion.database_id = "test-db"
        mock_load_config.return_value = mock_config

        # Mock migrator
        mock_migrator = Mock()
        mock_migrator.migrate.return_value = {
            "status": "completed",
            "report": "Migration completed successfully",
        }
        mock_migrator_class.return_value = mock_migrator

        # Run main
        with patch("builtins.print") as mock_print:
            main()

        # Verify
        mock_load_config.assert_called_once_with("config.yaml")
        mock_migrator_class.assert_called_once_with(mock_config)
        mock_migrator.migrate.assert_called_once_with(dry_run=False)

        # Verify success output
        mock_print.assert_any_call("MIGRATION COMPLETED SUCCESSFULLY")

    @patch("sys.argv", ["obsidian-to-notion", "--dry-run"])
    @patch("obsidian_to_notion.main.ObsidianToNotionMigrator")
    @patch("obsidian_to_notion.main.AppConfig.load_from_file")
    def test_main_dry_run(self, mock_load_config, mock_migrator_class):
        """Test main with dry-run flag."""
        # Mock config
        mock_config = Mock()
        mock_config.notion.token = "test-token"
        mock_config.notion.database_id = "test-db"
        mock_load_config.return_value = mock_config

        # Mock migrator
        mock_migrator = Mock()
        mock_migrator.migrate.return_value = {
            "status": "completed",
            "report": "Dry run completed",
        }
        mock_migrator_class.return_value = mock_migrator

        # Run main
        main()

        # Verify dry-run was passed
        mock_migrator.migrate.assert_called_once_with(dry_run=True)

    @patch("sys.argv", ["obsidian-to-notion"])
    @patch("obsidian_to_notion.main.AppConfig.load_from_file")
    def test_main_missing_token(self, mock_load_config):
        """Test main with missing Notion token."""
        # Mock config without token
        mock_config = Mock()
        mock_config.notion.token = None
        mock_config.notion.database_id = "test-db"
        mock_load_config.return_value = mock_config

        # Run main
        with patch("builtins.print") as mock_print:
            with pytest.raises(SystemExit) as exc_info:
                main()

        # Verify error message and exit code
        mock_print.assert_called_with(
            "Error: NOTION_TOKEN environment variable is required"
        )
        assert exc_info.value.code == 1

    @patch("sys.argv", ["obsidian-to-notion"])
    @patch("obsidian_to_notion.main.AppConfig.load_from_file")
    def test_main_missing_database_id(self, mock_load_config):
        """Test main with missing database ID."""
        # Mock config without database ID
        mock_config = Mock()
        mock_config.notion.token = "test-token"
        mock_config.notion.database_id = None
        mock_load_config.return_value = mock_config

        # Run main
        with patch("builtins.print") as mock_print:
            with pytest.raises(SystemExit) as exc_info:
                main()

        # Verify error message and exit code
        mock_print.assert_called_with(
            "Error: NOTION_DATABASE_ID environment variable is required"
        )
        assert exc_info.value.code == 1

    @patch("sys.argv", ["obsidian-to-notion", "--config", "custom.yaml"])
    @patch("obsidian_to_notion.main.ObsidianToNotionMigrator")
    @patch("obsidian_to_notion.main.AppConfig.load_from_file")
    def test_main_custom_config(self, mock_load_config, mock_migrator_class):
        """Test main with custom config file."""
        # Mock config
        mock_config = Mock()
        mock_config.notion.token = "test-token"
        mock_config.notion.database_id = "test-db"
        mock_load_config.return_value = mock_config

        # Mock migrator
        mock_migrator = Mock()
        mock_migrator.migrate.return_value = {"status": "completed", "report": "Done"}
        mock_migrator_class.return_value = mock_migrator

        # Run main
        main()

        # Verify custom config was loaded
        mock_load_config.assert_called_once_with("custom.yaml")

    @patch("sys.argv", ["obsidian-to-notion"])
    @patch("obsidian_to_notion.main.AppConfig.load_from_file")
    def test_main_exception_handling(self, mock_load_config):
        """Test main exception handling."""
        # Mock config to raise exception
        mock_load_config.side_effect = Exception("Config error")

        # Run main
        with patch("builtins.print") as mock_print:
            with pytest.raises(SystemExit) as exc_info:
                main()

        # Verify error was printed and exit code
        mock_print.assert_called_with("Migration failed: Config error")
        assert exc_info.value.code == 1


if __name__ == "__main__":
    unittest.main()
