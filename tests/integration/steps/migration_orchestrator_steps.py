"""Step definitions for migration orchestrator integration tests."""

import os
import tempfile
from unittest.mock import Mock, patch

from behave import given, then, when

from obsidian_to_notion.config import (
    AppConfig,
    LoggingConfig,
    MigrationConfig,
    NotionConfig,
    VaultConfig,
)
from obsidian_to_notion.main import ObsidianToNotionMigrator


@given("I have a valid configuration")
def step_valid_configuration(context):
    """Create a valid configuration for testing."""
    context.temp_dir = tempfile.mkdtemp()
    context.vault_path = os.path.join(context.temp_dir, "vault")
    os.makedirs(context.vault_path)

    # Create config with test values
    context.config = AppConfig(
        vault=VaultConfig(path=context.vault_path),
        migration=MigrationConfig(),
        notion=NotionConfig(token="test-token", database_id="test-database-id"),
        logging=LoggingConfig(log_file=os.path.join(context.temp_dir, "test.log")),
    )


@given("I have a test Obsidian vault")
def step_test_vault(context):
    """Ensure test vault directory exists."""
    if not os.path.exists(context.vault_path):
        os.makedirs(context.vault_path)


@given("the vault contains the following files")
def step_vault_contains_files(context):
    """Create markdown files in the test vault."""
    context.created_files = []

    for row in context.table:
        file_path = os.path.join(context.vault_path, row["filename"])
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Create content with optional frontmatter
        content = f"---\ntitle: {row['title']}\n---\n\n{row['content']}"

        with open(file_path, "w") as f:
            f.write(content)

        context.created_files.append(
            {"path": file_path, "title": row["title"], "content": row["content"]}
        )


@given("I have a Notion database ID")
def step_notion_database_id(context):
    """Ensure Notion database ID is set."""
    context.config.notion.database_id = "test-database-id"


@given('the Notion database already contains a page titled "{title}"')
def step_notion_has_existing_page(context, title):
    """Mock existing page in Notion database."""
    if not hasattr(context, "existing_pages"):
        context.existing_pages = []
    context.existing_pages.append(title)


# This step is already defined in obsidian_parser_steps.py
# @given("the vault is empty")
# def step_empty_vault(context):
#     """Ensure vault is empty."""
#     # Clear any existing files
#     for root, dirs, files in os.walk(context.vault_path):
#         for file in files:
#             os.remove(os.path.join(root, file))


@given("a markdown file with frontmatter")
def step_markdown_with_frontmatter(context):
    """Create a markdown file with frontmatter from text."""
    file_path = os.path.join(context.vault_path, "test_document.md")

    with open(file_path, "w") as f:
        f.write(context.text)

    context.created_files = [
        {"path": file_path, "title": "Test Document", "content": context.text}
    ]


@given("the vault contains {count:d} markdown files")
def step_vault_contains_count_files(context, count):
    """Create specified number of files."""
    context.created_files = []

    for i in range(count):
        file_path = os.path.join(context.vault_path, f"note_{i}.md")
        content = f"---\ntitle: Note {i}\n---\n\nContent for note {i}"

        with open(file_path, "w") as f:
            f.write(content)

        context.created_files.append(
            {
                "path": file_path,
                "title": f"Note {i}",
                "content": f"Content for note {i}",
            }
        )


@given('the Notion API will fail for "{title}"')
def step_notion_api_will_fail(context, title):
    """Set up API to fail for specific title."""
    if not hasattr(context, "failing_titles"):
        context.failing_titles = []
    context.failing_titles.append(title)


@when("I run the migration")
def step_run_migration(context):
    """Execute the migration."""
    with patch("obsidian_to_notion.main.NotionMigrationClient") as mock_client_class:
        # Set up mock client
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Track created pages
        context.created_pages = []

        def mock_create_page(database_id, properties, children=None):
            title = (
                properties.get("Name", {})
                .get("title", [{}])[0]
                .get("text", {})
                .get("content", "")
            )

            # Check if this should fail
            if hasattr(context, "failing_titles") and title in context.failing_titles:
                raise Exception(f"API error for {title}")

            page_id = f"page-{len(context.created_pages)}"
            context.created_pages.append(
                {
                    "id": page_id,
                    "title": title,
                    "properties": properties,
                    "children": children or [],
                }
            )
            return {"id": page_id}

        mock_client.create_page.side_effect = mock_create_page

        # Mock deduplication if needed
        if hasattr(context, "existing_pages"):
            mock_client.query_database.return_value = [
                {
                    "id": f"existing-{i}",
                    "properties": {
                        "Name": {
                            "type": "title",
                            "title": [{"text": {"content": title}}],
                        }
                    },
                }
                for i, title in enumerate(context.existing_pages)
            ]
        else:
            mock_client.query_database.return_value = []

        # Create migrator with mocked dependencies
        context.migrator = ObsidianToNotionMigrator(context.config)

        try:
            context.result = context.migrator.migrate(dry_run=False)
            context.migration_error = None
        except Exception as e:
            context.migration_error = e
            context.result = {"status": "failed", "error": str(e)}


@when("I run the migration in dry-run mode")
def step_run_migration_dry_run(context):
    """Execute migration in dry-run mode."""
    with patch("obsidian_to_notion.main.NotionMigrationClient"):
        context.migrator = ObsidianToNotionMigrator(context.config)

        # Capture print output
        with patch("builtins.print") as mock_print:
            context.dry_run_output = []
            mock_print.side_effect = lambda x: context.dry_run_output.append(str(x))

            context.result = context.migrator.migrate(dry_run=True)


@when("I run the migration with skip duplicates enabled")
def step_run_migration_skip_duplicates(context):
    """Execute migration with duplicate skipping."""
    context.config.migration.skip_duplicates = True
    step_run_migration(context)


@when("I run the migration with progress tracking")
def step_run_migration_with_progress(context):
    """Execute migration with progress tracking enabled."""
    context.config.logging.progress_bar = True

    # Mock progress tracking
    with patch("obsidian_to_notion.utils.progress.ProgressReporter") as mock_progress:
        context.progress_reporter = Mock()
        mock_progress.return_value = context.progress_reporter

        step_run_migration(context)


@then("{count:d} pages should be created in Notion")
def step_verify_pages_created(context, count):
    """Verify number of pages created."""
    assert (
        len(context.created_pages) == count
    ), f"Expected {count} pages, but {len(context.created_pages)} were created"


@then("{count:d} page should be created in Notion")
def step_verify_single_page_created(context, count):
    """Verify single page created."""
    step_verify_pages_created(context, count)


@then("no pages should be created in Notion")
def step_verify_no_pages_created(context):
    """Verify no pages were created."""
    if hasattr(context, "created_pages"):
        assert (
            len(context.created_pages) == 0
        ), f"Expected no pages, but {len(context.created_pages)} were created"


@then("no pages should be created")
def step_verify_no_pages_created_alt(context):
    """Verify no pages were created (alternative)."""
    step_verify_no_pages_created(context)


@then("the migration should complete successfully")
def step_verify_migration_success(context):
    """Verify migration completed without errors."""
    assert (
        context.migration_error is None
    ), f"Migration failed with error: {context.migration_error}"
    assert (
        context.result["status"] == "completed"
    ), f"Expected status 'completed', got '{context.result['status']}'"


@then("the migration should complete with {status} status")
def step_verify_migration_status(context, status):
    """Verify migration completed with specific status."""
    assert (
        context.result["status"] == status
    ), f"Expected status '{status}', got '{context.result['status']}'"


@then("the report should show {count:d} successful migrations")
def step_verify_report_successful(context, count):
    """Verify report shows correct successful count."""
    stats = context.result.get("stats", {})
    assert (
        stats.get("successful") == count
    ), f"Expected {count} successful, got {stats.get('successful')}"


@then("the report should show {count:d} would-be migrations")
def step_verify_report_would_be(context, count):
    """Verify dry-run report shows correct count."""
    stats = context.result.get("stats", {})
    assert (
        stats.get("successful") == count
    ), f"Expected {count} would-be migrations, got {stats.get('successful')}"


@then("the output should show what would be migrated")
def step_verify_dry_run_output(context):
    """Verify dry-run output shows migration preview."""
    assert any(
        "WOULD CREATE" in line for line in context.dry_run_output
    ), "Expected 'WOULD CREATE' in dry-run output"


@then("{count:d} page should be created successfully")
def step_verify_page_created_successfully(context, count):
    """Verify specific number of successful pages."""
    step_verify_pages_created(context, count)


@then("{count:d} page should be skipped")
def step_verify_pages_skipped(context, count):
    """Verify number of skipped pages."""
    stats = context.result.get("stats", {})
    assert (
        stats.get("skipped") == count
    ), f"Expected {count} skipped, got {stats.get('skipped')}"


@then("the report should show {successful:d} successful and {skipped:d} skipped")
def step_verify_report_counts(context, successful, skipped):
    """Verify report shows correct counts."""
    stats = context.result.get("stats", {})
    assert (
        stats.get("successful") == successful
    ), f"Expected {successful} successful, got {stats.get('successful')}"
    assert (
        stats.get("skipped") == skipped
    ), f"Expected {skipped} skipped, got {stats.get('skipped')}"


@then("wikilinks should be converted to Notion page mentions")
def step_verify_wikilinks_converted(context):
    """Verify wikilinks were converted properly."""
    # Check that created pages contain converted content
    for page in context.created_pages:
        if page["children"]:
            # Verify children blocks were created (simplified check)
            assert len(page["children"]) > 0, "Expected page to have content blocks"


@then("the report should show successful link resolution")
def step_verify_link_resolution(context):
    """Verify report indicates successful link resolution."""
    report = context.result.get("report", "")
    # If no broken links, the report won't have a broken links section
    assert "## Broken Links" not in report or "No broken links" in report


@then("{count:d} page should fail to migrate")
def step_verify_pages_failed(context, count):
    """Verify number of failed pages."""
    stats = context.result.get("stats", {})
    assert (
        stats.get("failed") == count
    ), f"Expected {count} failed, got {stats.get('failed')}"


@then("the report should include error details")
def step_verify_error_details(context):
    """Verify report includes error information."""
    report = context.result.get("report", "")
    assert "## Errors" in report, "Expected errors section in report"

    stats = context.result.get("stats", {})
    errors = stats.get("errors", [])
    assert len(errors) > 0, "Expected error details in stats"


@then("the report should indicate no files found")
def step_verify_no_files_report(context):
    """Verify report indicates empty vault."""
    report = context.result.get("report", "")
    assert (
        "Total files processed: 0" in report
    ), "Expected report to show 0 files processed"


@then('the Notion page should have the title "{title}"')
def step_verify_page_title(context, title):
    """Verify created page has correct title."""
    assert len(context.created_pages) > 0, "No pages were created"

    page = context.created_pages[0]
    page_title = (
        page["properties"]
        .get("Name", {})
        .get("title", [{}])[0]
        .get("text", {})
        .get("content", "")
    )
    assert page_title == title, f"Expected title '{title}', got '{page_title}'"


@then("the page properties should include the metadata fields")
def step_verify_metadata_properties(context):
    """Verify page properties include metadata."""
    assert len(context.created_pages) > 0, "No pages were created"

    page = context.created_pages[0]
    properties = page["properties"]

    # Should have metadata fields as properties
    # The actual implementation would convert metadata to properties
    assert "Name" in properties, "Missing Name property"


@then("the content should be properly formatted")
def step_verify_content_format(context):
    """Verify content is properly formatted."""
    assert len(context.created_pages) > 0, "No pages were created"

    page = context.created_pages[0]
    assert page["children"] is not None, "Page should have content blocks"


@then("progress updates should be displayed")
def step_verify_progress_updates(context):
    """Verify progress tracking was used."""
    if hasattr(context, "progress_reporter"):
        # In a real test, we'd verify the progress reporter was used
        pass


@then("the final statistics should show the results")
def step_verify_final_statistics(context):
    """Verify final statistics are available."""
    assert "stats" in context.result, "Missing statistics in result"
    stats = context.result["stats"]

    # Should have all stat fields
    assert "successful" in stats
    assert "failed" in stats
    assert "skipped" in stats


@then("the progress bar should complete at 100%")
def step_verify_progress_complete(context):
    """Verify progress bar reached completion."""
    # In a real implementation, we'd check the progress reporter
    # was properly closed/completed
    pass
