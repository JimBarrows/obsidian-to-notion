"""Configuration management for Obsidian to Notion migration."""

import os
from pathlib import Path
from typing import Dict, Any

import yaml
from dotenv import load_dotenv


def load_config(config_path: Path) -> Dict[str, Any]:
    """Load configuration from YAML file and environment variables.
    
    Args:
        config_path: Path to the YAML configuration file
        
    Returns:
        Dictionary containing configuration settings
    """
    # Load environment variables
    load_dotenv()
    
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