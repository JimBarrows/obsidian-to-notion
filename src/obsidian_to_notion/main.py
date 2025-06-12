"""Main entry point for the Obsidian to Notion migration tool."""

import argparse
import logging
import sys
from pathlib import Path

from .config import load_config
from .utils.error_handling import setup_error_handling
from .utils.progress import ProgressReporter


def main():
    """Main function for the Obsidian to Notion migration tool."""
    parser = argparse.ArgumentParser(
        description="Migrate Obsidian markdown files to Notion"
    )
    parser.add_argument(
        "obsidian_vault",
        type=Path,
        help="Path to Obsidian vault directory"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without actually uploading to Notion"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Setup error handling
    setup_error_handling()
    
    try:
        # Load configuration
        config = load_config(args.config)
        
        # Initialize progress reporter
        progress = ProgressReporter()
        
        # TODO: Implement migration logic
        logging.info(f"Starting migration from {args.obsidian_vault}")
        
        if args.dry_run:
            logging.info("Running in dry-run mode - no changes will be made to Notion")
        
    except Exception as e:
        logging.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()