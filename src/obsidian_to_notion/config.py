"""Configuration management for Obsidian to Notion migration."""

import os
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class VaultConfig:
    """Configuration for the Obsidian vault."""
    path: str


@dataclass 
class MigrationConfig:
    """Configuration for the migration process."""
    batch_size: int = 50
    parallel_workers: int = 3
    retry_attempts: int = 3
    skip_duplicates: bool = True
    upload_attachments: bool = True
    max_file_size_mb: int = 5


@dataclass
class NotionConfig:
    """Configuration for Notion API integration."""
    api_url: str = "https://api.notion.com/v1"
    timeout: int = 30
    rate_limit_requests_per_second: int = 3
    token: Optional[str] = None
    database_id: Optional[str] = None


@dataclass
class LoggingConfig:
    """Configuration for logging and progress reporting."""
    level: str = "INFO"
    progress_bar: bool = True
    log_file: str = "migration.log"


@dataclass
class AppConfig:
    """Main application configuration."""
    vault: VaultConfig
    migration: MigrationConfig
    notion: NotionConfig
    logging: LoggingConfig
    
    @classmethod
    def load_from_file(cls, config_path: str = "config.yaml") -> "AppConfig":
        """Load configuration from YAML file and environment variables.
        
        Args:
            config_path: Path to the YAML configuration file
            
        Returns:
            AppConfig instance with loaded configuration
        """
        config_path_obj = Path(config_path)
        if not config_path_obj.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        with open(config_path_obj, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Load vault configuration
        vault = VaultConfig(**config_data['vault'])
        
        # Load migration configuration
        migration = MigrationConfig(**config_data.get('migration', {}))
        
        # Load Notion configuration with environment variable overrides
        notion_data = config_data.get('notion', {}).copy()
        notion_data['token'] = os.getenv('NOTION_TOKEN')
        notion_data['database_id'] = os.getenv('NOTION_DATABASE_ID')
        notion = NotionConfig(**notion_data)
        
        # Load logging configuration
        logging_config = LoggingConfig(**config_data.get('logging', {}))
        
        return cls(
            vault=vault,
            migration=migration,
            notion=notion,
            logging=logging_config
        )
    
    def validate(self) -> None:
        """Validate the configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate vault path exists
        vault_path = Path(self.vault.path)
        if not vault_path.exists():
            raise ValueError(f"Vault path does not exist: {self.vault.path}")
        if not vault_path.is_dir():
            raise ValueError(f"Vault path is not a directory: {self.vault.path}")
        
        # Validate Notion token
        if not self.notion.token:
            raise ValueError("NOTION_TOKEN environment variable is required")
        
        # Validate numeric values
        if self.migration.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if self.migration.parallel_workers <= 0:
            raise ValueError("parallel_workers must be positive")
        if self.migration.retry_attempts < 0:
            raise ValueError("retry_attempts must be non-negative")
        if self.migration.max_file_size_mb <= 0:
            raise ValueError("max_file_size_mb must be positive")
        if self.notion.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.notion.rate_limit_requests_per_second <= 0:
            raise ValueError("rate_limit_requests_per_second must be positive")


# Backward compatibility function
def load_config(config_path: Path) -> dict:
    """Legacy function to load configuration.
    
    Args:
        config_path: Path to the YAML configuration file
        
    Returns:
        Dictionary containing configuration settings
    """
    # Convert string to Path if necessary
    if isinstance(config_path, str):
        config_path = Path(config_path)
    
    # Load YAML configuration
    config = {}
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}
    
    # Override with environment variables
    if notion_token := os.getenv('NOTION_TOKEN'):
        config['notion_token'] = notion_token
    
    if notion_workspace_id := os.getenv('NOTION_WORKSPACE_ID'):
        config['notion_workspace_id'] = notion_workspace_id
    
    # Set defaults
    config.setdefault('skip_patterns', ['.obsidian/', '.trash/'])
    config.setdefault('attachment_extensions', [
        '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.mp4', '.mov'
    ])
    config.setdefault('max_retries', 3)
    config.setdefault('batch_size', 10)
    
    return config