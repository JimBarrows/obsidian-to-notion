"""Unit tests for configuration module."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from obsidian_to_notion.config import (
    AppConfig,
    LoggingConfig,
    MigrationConfig,
    NotionConfig,
    VaultConfig,
)


class TestVaultConfig(unittest.TestCase):
    """Test VaultConfig dataclass."""

    def test_vault_config_creation(self):
        """Test creating a VaultConfig instance."""
        config = VaultConfig(path="/test/vault")
        self.assertEqual(config.path, "/test/vault")


class TestMigrationConfig(unittest.TestCase):
    """Test MigrationConfig dataclass."""

    def test_migration_config_defaults(self):
        """Test MigrationConfig default values."""
        config = MigrationConfig()
        self.assertEqual(config.batch_size, 50)
        self.assertEqual(config.parallel_workers, 3)
        self.assertEqual(config.retry_attempts, 3)
        self.assertTrue(config.skip_duplicates)
        self.assertTrue(config.upload_attachments)
        self.assertEqual(config.max_file_size_mb, 5)

    def test_migration_config_custom_values(self):
        """Test MigrationConfig with custom values."""
        config = MigrationConfig(
            batch_size=100,
            parallel_workers=5,
            retry_attempts=5,
            skip_duplicates=False,
            upload_attachments=False,
            max_file_size_mb=10,
        )
        self.assertEqual(config.batch_size, 100)
        self.assertEqual(config.parallel_workers, 5)
        self.assertEqual(config.retry_attempts, 5)
        self.assertFalse(config.skip_duplicates)
        self.assertFalse(config.upload_attachments)
        self.assertEqual(config.max_file_size_mb, 10)


class TestNotionConfig(unittest.TestCase):
    """Test NotionConfig dataclass."""

    def test_notion_config_defaults(self):
        """Test NotionConfig default values."""
        config = NotionConfig()
        self.assertEqual(config.api_url, "https://api.notion.com/v1")
        self.assertEqual(config.timeout, 30)
        self.assertEqual(config.rate_limit_requests_per_second, 3)
        self.assertIsNone(config.token)
        self.assertIsNone(config.database_id)

    def test_notion_config_custom_values(self):
        """Test NotionConfig with custom values."""
        config = NotionConfig(
            api_url="https://custom.api.com",
            timeout=60,
            rate_limit_requests_per_second=5,
            token="test-token",
            database_id="test-db-id",
        )
        self.assertEqual(config.api_url, "https://custom.api.com")
        self.assertEqual(config.timeout, 60)
        self.assertEqual(config.rate_limit_requests_per_second, 5)
        self.assertEqual(config.token, "test-token")
        self.assertEqual(config.database_id, "test-db-id")


class TestLoggingConfig(unittest.TestCase):
    """Test LoggingConfig dataclass."""

    def test_logging_config_defaults(self):
        """Test LoggingConfig default values."""
        config = LoggingConfig()
        self.assertEqual(config.level, "INFO")
        self.assertTrue(config.progress_bar)
        self.assertEqual(config.log_file, "migration.log")

    def test_logging_config_custom_values(self):
        """Test LoggingConfig with custom values."""
        config = LoggingConfig(level="DEBUG", progress_bar=False, log_file="custom.log")
        self.assertEqual(config.level, "DEBUG")
        self.assertFalse(config.progress_bar)
        self.assertEqual(config.log_file, "custom.log")


class TestAppConfig(unittest.TestCase):
    """Test AppConfig dataclass and methods."""

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

    def test_load_from_file_success(self):
        """Test loading configuration from YAML file."""
        config_data = {
            "vault": {"path": str(self.vault_path)},
            "migration": {"batch_size": 100},
            "notion": {"timeout": 60},
            "logging": {"level": "DEBUG"},
        }
        with open(self.config_file, "w") as f:
            yaml.dump(config_data, f)

        with patch.dict(os.environ, {"NOTION_TOKEN": "test-token"}):
            config = AppConfig.load_from_file(str(self.config_file))

        self.assertEqual(config.vault.path, str(self.vault_path))
        self.assertEqual(config.migration.batch_size, 100)
        self.assertEqual(config.notion.timeout, 60)
        self.assertEqual(config.notion.token, "test-token")
        self.assertEqual(config.logging.level, "DEBUG")

    def test_load_from_file_not_found(self):
        """Test loading configuration from non-existent file."""
        with self.assertRaises(FileNotFoundError):
            AppConfig.load_from_file("/non/existent/config.yaml")

    def test_load_from_file_with_env_override(self):
        """Test environment variables override config file."""
        config_data = {
            "vault": {"path": str(self.vault_path)},
        }
        with open(self.config_file, "w") as f:
            yaml.dump(config_data, f)

        with patch.dict(
            os.environ,
            {"NOTION_TOKEN": "env-token", "NOTION_DATABASE_ID": "env-db-id"},
        ):
            config = AppConfig.load_from_file(str(self.config_file))

        self.assertEqual(config.notion.token, "env-token")
        self.assertEqual(config.notion.database_id, "env-db-id")

    def test_validate_success(self):
        """Test successful validation."""
        config = AppConfig(
            vault=VaultConfig(path=str(self.vault_path)),
            migration=MigrationConfig(),
            notion=NotionConfig(token="test-token"),
            logging=LoggingConfig(),
        )
        # Should not raise
        config.validate()

    def test_validate_vault_not_exists(self):
        """Test validation fails when vault doesn't exist."""
        config = AppConfig(
            vault=VaultConfig(path="/non/existent/path"),
            migration=MigrationConfig(),
            notion=NotionConfig(token="test-token"),
            logging=LoggingConfig(),
        )
        with self.assertRaises(ValueError) as cm:
            config.validate()
        self.assertIn("Vault path does not exist", str(cm.exception))

    def test_validate_vault_not_directory(self):
        """Test validation fails when vault is not a directory."""
        file_path = Path(self.temp_dir) / "file.txt"
        file_path.write_text("test")

        config = AppConfig(
            vault=VaultConfig(path=str(file_path)),
            migration=MigrationConfig(),
            notion=NotionConfig(token="test-token"),
            logging=LoggingConfig(),
        )
        with self.assertRaises(ValueError) as cm:
            config.validate()
        self.assertIn("Vault path is not a directory", str(cm.exception))

    def test_validate_no_token(self):
        """Test validation fails without Notion token."""
        config = AppConfig(
            vault=VaultConfig(path=str(self.vault_path)),
            migration=MigrationConfig(),
            notion=NotionConfig(),
            logging=LoggingConfig(),
        )
        with self.assertRaises(ValueError) as cm:
            config.validate()
        self.assertIn(
            "NOTION_TOKEN environment variable is required", str(cm.exception)
        )

    def test_validate_invalid_batch_size(self):
        """Test validation fails with invalid batch size."""
        config = AppConfig(
            vault=VaultConfig(path=str(self.vault_path)),
            migration=MigrationConfig(batch_size=0),
            notion=NotionConfig(token="test-token"),
            logging=LoggingConfig(),
        )
        with self.assertRaises(ValueError) as cm:
            config.validate()
        self.assertIn("batch_size must be positive", str(cm.exception))

    def test_validate_invalid_workers(self):
        """Test validation fails with invalid workers."""
        config = AppConfig(
            vault=VaultConfig(path=str(self.vault_path)),
            migration=MigrationConfig(parallel_workers=-1),
            notion=NotionConfig(token="test-token"),
            logging=LoggingConfig(),
        )
        with self.assertRaises(ValueError) as cm:
            config.validate()
        self.assertIn("parallel_workers must be positive", str(cm.exception))

    def test_validate_invalid_timeout(self):
        """Test validation fails with invalid timeout."""
        config = AppConfig(
            vault=VaultConfig(path=str(self.vault_path)),
            migration=MigrationConfig(),
            notion=NotionConfig(token="test-token", timeout=0),
            logging=LoggingConfig(),
        )
        with self.assertRaises(ValueError) as cm:
            config.validate()
        self.assertIn("timeout must be positive", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
