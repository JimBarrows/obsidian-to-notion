"""Main entry point for the Obsidian to Notion migration tool."""

import argparse
import logging
import sys
from pathlib import Path

from .config import AppConfig
from .utils.error_handling import setup_error_handling


def setup_logging(config: AppConfig, verbose: bool = False) -> None:
    """Set up logging configuration.

    Args:
        config: Application configuration
        verbose: Whether to enable verbose logging
    """
    log_level = logging.DEBUG if verbose else getattr(logging, config.logging.level)

    # Configure console logging
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)

    # Configure file logging
    file_handler = logging.FileHandler(config.logging.log_file)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(console_formatter)

    # Set up root logger
    logging.root.setLevel(log_level)
    logging.root.addHandler(console_handler)
    logging.root.addHandler(file_handler)


def main() -> None:
    """Main function for the Obsidian to Notion migration tool."""
    parser = argparse.ArgumentParser(
        description="Migrate Obsidian markdown files to Notion"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    parser.add_argument(
        "--vault", type=Path, help="Override vault path from configuration"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without actually uploading to Notion",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup error handling
    setup_error_handling()

    try:
        # Load configuration
        config = AppConfig.load_from_file(args.config)

        # Override vault path if provided
        if args.vault:
            config.vault.path = str(args.vault)

        # Set up logging
        setup_logging(config, args.verbose)
        logger = logging.getLogger(__name__)

        # Validate configuration
        try:
            config.validate()
        except ValueError as e:
            logger.error(f"Invalid configuration: {e}")
            sys.exit(1)

        # Log startup information
        logger.info("Starting Obsidian to Notion migration")
        logger.info(f"Vault path: {config.vault.path}")
        logger.info(f"Batch size: {config.migration.batch_size}")
        logger.info(f"Parallel workers: {config.migration.parallel_workers}")

        if args.dry_run:
            logger.info("Running in dry-run mode - no changes will be made to Notion")

        # TODO: Implement migration logic
        logger.info("Migration logic not yet implemented")

    except FileNotFoundError as e:
        logging.error(f"Configuration file not found: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
