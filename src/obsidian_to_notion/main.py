#!/usr/bin/env python3
"""Obsidian to Notion Migration Tool."""

import argparse
import logging
import sys
from typing import Any, Dict, List

from .config import AppConfig
from .notion import DeduplicationManager, NotionMigrationClient
from .parsers import ObsidianVaultProcessor
from .transformers import WikilinkConverter
from .utils import MigrationError, ProgressTracker
from .utils.error_handling import (
    create_error_context,
    log_error_with_context,
    setup_error_handling,
)


class ObsidianToNotionMigrator:
    """Main orchestrator for Obsidian to Notion migration."""

    def __init__(self, config: AppConfig) -> None:
        """Initialize the migration orchestrator with configuration."""
        self.config = config
        self.vault_processor = ObsidianVaultProcessor(config.vault.path)
        if not config.notion.token:
            raise ValueError("Notion token is required")
        self.notion_client = NotionMigrationClient(
            config.notion.token, config.notion.rate_limit_requests_per_second
        )
        self.wikilink_converter = WikilinkConverter({})
        if not config.notion.database_id:
            raise ValueError("Notion database ID is required")
        self.dedup_manager = DeduplicationManager(
            self.notion_client, config.notion.database_id
        )

        # Setup logging
        logging.basicConfig(
            level=getattr(logging, config.logging.level),
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(config.logging.log_file),
                logging.StreamHandler(sys.stdout),
            ],
        )
        self.logger = logging.getLogger(__name__)

        # Setup enhanced error handling
        setup_error_handling()

    def migrate(self, dry_run: bool = False) -> Dict[str, Any]:
        """Execute complete migration process."""
        self.logger.info("Starting Obsidian to Notion migration")

        try:
            # Phase 1: Process vault
            self.logger.info("Phase 1: Processing Obsidian vault...")
            vault_data = self.vault_processor.process_vault()

            if not vault_data["markdown_files"]:
                self.logger.warning("No markdown files found in vault")
                return {"status": "no_files", "stats": {}}

            # Phase 2: Load existing pages for deduplication
            if self.config.migration.skip_duplicates:
                self.logger.info("Phase 2: Loading existing Notion pages...")
                self.dedup_manager.load_existing_pages()

            # Phase 3: Create/update pages
            self.logger.info("Phase 3: Migrating pages to Notion...")
            if dry_run:
                self.logger.info("DRY RUN MODE - No actual changes will be made")
                migration_stats = self._dry_run_migration(vault_data["markdown_files"])
            else:
                migration_stats = self._execute_migration(vault_data["markdown_files"])

            # Phase 4: Generate report
            self.logger.info("Phase 4: Generating migration report...")
            report = self._generate_report(migration_stats, vault_data)

            self.logger.info("Migration completed successfully")
            return {"status": "completed", "stats": migration_stats, "report": report}

        except Exception as e:
            context = create_error_context(
                phase="migration_orchestration",
                vault_path=self.config.vault.path,
                database_id=self.config.notion.database_id,
                dry_run=dry_run,
                error_type=type(e).__name__,
            )
            migration_error = MigrationError(f"Migration failed: {e}")
            log_error_with_context(self.logger, migration_error, context)
            raise migration_error from e

    def _execute_migration(
        self, markdown_files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute the actual migration."""
        stats: Dict[str, Any] = {
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
        }

        # ProgressTracker is actually ProgressReporter and doesn't support
        # context manager
        progress = ProgressTracker()
        progress.start_main(len(markdown_files), "Migrating files")
        try:
            for file_info in markdown_files:
                try:
                    result = self._migrate_single_file(file_info)

                    if result["status"] == "skipped":
                        progress.update_main(1)
                        progress.set_main_desc("skipped")
                        stats["skipped"] += 1
                    elif result["status"] == "success":
                        progress.update_main(1)
                        progress.set_main_desc("successful")
                        stats["successful"] += 1
                        # Add to wikilink cache for link resolution
                        self.wikilink_converter.add_page_to_cache(
                            file_info["title"], result["page_id"]
                        )
                    else:
                        progress.update_main(1)
                        progress.set_main_desc(f"failed: {result.get('error')}")
                        stats["failed"] += 1
                        stats["errors"].append(
                            {"file": file_info["title"], "error": result.get("error")}
                        )

                    # Progress reporter doesn't have set_postfix method

                except Exception as e:
                    context = create_error_context(
                        phase="file_migration",
                        file_path=str(file_info.get("path", "")),
                        file_title=file_info["title"],
                        file_index=markdown_files.index(file_info),
                        total_files=len(markdown_files),
                        error_type=type(e).__name__,
                        stats_so_far={
                            "successful": stats["successful"],
                            "failed": stats["failed"],
                            "skipped": stats["skipped"],
                        },
                    )
                    log_error_with_context(self.logger, e, context)

                    error_msg = f"Error migrating {file_info['title']}: {e}"
                    progress.update_main(1)
                    progress.set_main_desc(f"failed: {error_msg}")
                    stats["failed"] += 1
                    stats["errors"].append(
                        {"file": file_info["title"], "error": str(e)}
                    )
        finally:
            progress.close()
        return stats

    def _dry_run_migration(
        self, markdown_files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Simulate migration without making changes."""
        stats: Dict[str, Any] = {
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
        }

        for file_info in markdown_files:
            title = file_info["title"]

            if (
                self.config.migration.skip_duplicates
                and self.dedup_manager.should_skip_page(title)
            ):
                print(f"WOULD SKIP: {title} (already exists)")
                stats["skipped"] += 1
            else:
                print(f"WOULD CREATE: {title}")
                stats["successful"] += 1

        return stats

    def _migrate_single_file(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate a single file to Notion."""
        title = file_info["title"]

        # Check for duplicates
        if (
            self.config.migration.skip_duplicates
            and self.dedup_manager.should_skip_page(title)
        ):
            return {"status": "skipped", "reason": "duplicate"}

        try:
            # Convert content
            converted_content = self.wikilink_converter.convert_content(
                file_info["content"], file_info["wikilinks"]
            )

            # Prepare Notion page properties
            properties = {
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": self.vault_processor.sanitize_for_notion(
                                    title
                                )
                            }
                        }
                    ]
                }
            }

            # Add metadata as properties if present
            for key, value in file_info["metadata"].items():
                if key != "title" and isinstance(value, (str, int, float, bool)):
                    properties[key] = {"rich_text": [{"text": {"content": str(value)}}]}

            # Create page content blocks
            children = self._content_to_notion_blocks(converted_content)

            # Create page in Notion
            # database_id was already validated in __init__
            if self.config.notion.database_id is None:
                raise ValueError("Database ID is required but not set")
            page = self.notion_client.create_page(
                database_id=self.config.notion.database_id,
                properties=properties,
                children=children,
            )

            if page:
                return {"status": "success", "page_id": page["id"]}
            else:
                return {"status": "failed", "error": "Failed to create page"}

        except Exception as e:
            context = create_error_context(
                phase="single_file_migration",
                file_path=str(file_info.get("path", "")),
                file_title=title,
                has_wikilinks=bool(file_info.get("wikilinks")),
                num_wikilinks=len(file_info.get("wikilinks", [])),
                has_metadata=bool(file_info.get("metadata")),
                error_type=type(e).__name__,
            )
            log_error_with_context(self.logger, e, context)
            return {"status": "failed", "error": str(e)}

    def _content_to_notion_blocks(self, content: str) -> List[Dict[str, Any]]:
        """Convert markdown content to Notion blocks."""
        if not content.strip():
            return []

        # Simple implementation - convert to paragraph blocks
        # In a full implementation, you'd parse markdown properly
        lines = content.split("\n")
        blocks = []

        current_paragraph: List[str] = []

        for line in lines:
            line = line.strip()
            if not line:
                if current_paragraph:
                    blocks.append(
                        {
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [
                                    {"text": {"content": "\n".join(current_paragraph)}}
                                ]
                            },
                        }
                    )
                    current_paragraph = []
            else:
                current_paragraph.append(line)

        # Add final paragraph if exists
        if current_paragraph:
            blocks.append(
                {
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"text": {"content": "\n".join(current_paragraph)}}
                        ]
                    },
                }
            )

        return blocks

    def _generate_report(
        self, stats: Dict[str, Any], vault_data: Dict[str, Any]
    ) -> str:
        """Generate migration summary report."""
        total_files = len(vault_data["markdown_files"])
        total_attachments = len(vault_data["attachments"])

        report = [
            "# Migration Report",
            "## Summary",
            f"- Total files processed: {total_files}",
            f"- Successfully migrated: {stats['successful']}",
            f"- Skipped (duplicates): {stats['skipped']}",
            f"- Failed: {stats['failed']}",
            f"- Total attachments found: {total_attachments}",
            "",
        ]

        if stats["errors"]:
            report.extend(["## Errors", ""])
            for error in stats["errors"]:
                report.append(f"- **{error['file']}**: {error['error']}")
            report.append("")

        # Add broken links report
        broken_links_report = self.wikilink_converter.get_broken_links_report()
        if "No broken links" not in broken_links_report:
            report.extend(["## Broken Links", broken_links_report])

        return "\n".join(report)


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
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Migrate Obsidian vault to Notion")
    parser.add_argument(
        "--config", default="config.yaml", help="Configuration file path"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes",
    )

    args = parser.parse_args()

    # Set up enhanced error handling early
    setup_error_handling()

    try:
        # Load configuration
        config = AppConfig.load_from_file(args.config)

        # Validate required environment variables
        if not config.notion.token:
            print("Error: NOTION_TOKEN environment variable is required")
            sys.exit(1)

        if not config.notion.database_id:
            print("Error: NOTION_DATABASE_ID environment variable is required")
            sys.exit(1)

        # Create migrator and run
        migrator = ObsidianToNotionMigrator(config)
        result = migrator.migrate(dry_run=args.dry_run)

        if result["status"] == "completed":
            print("\n" + "=" * 50)
            print("MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 50)
            print(result["report"])
        else:
            print(f"Migration status: {result['status']}")

    except Exception as e:
        # Check if it's a Notion API error and provide more helpful context
        error_message = str(e)

        if "database" in error_message.lower() and (
            "not found" in error_message.lower() or "Could not find" in error_message
        ):
            print("\n" + "=" * 70)
            print("DATABASE CONNECTION ERROR")
            print("=" * 70)
            print(f"\n{error_message}\n")
            print("To resolve this issue:")
            print("1. Verify your NOTION_DATABASE_ID is correct")
            print("2. Ensure the database is shared with your integration:")
            print("   - Open the database in Notion")
            print("   - Click 'Share' in the top right")
            print("   - Invite your integration by name")
            print("3. Check that your integration has the necessary permissions\n")
            print(
                "For more information, see: "
                "https://developers.notion.com/docs/authorization"
            )
            print("=" * 70)
        else:
            print(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
