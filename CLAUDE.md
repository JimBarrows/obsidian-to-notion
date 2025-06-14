# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Obsidian to Notion Migration Tool - A Python utility for migrating Obsidian markdown files to Notion with support for wikilink conversion, file attachments, and deduplication.

## Project Structure

```
obsidian-to-notion/
├── src/obsidian_to_notion/     # Main package
│   ├── main.py                 # CLI entry point
│   ├── config.py               # Configuration management
│   ├── parsers/                # Obsidian parsing modules
│   │   └── obsidian_parser.py  # Markdown and wikilink parser
│   ├── notion/                 # Notion API integration
│   │   └── client.py           # Notion API wrapper
│   ├── transformers/           # Content transformation
│   │   └── wikilink_converter.py # Convert Obsidian links to Notion
│   └── utils/                  # Utility modules
│       ├── progress.py         # Progress reporting
│       └── error_handling.py   # Error handling utilities
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests
│   │   └── test_obsidian_parser.py
│   └── integration/            # BDD integration tests
│       ├── features/           # Gherkin feature files
│       │   └── obsidian_parser.feature
│       └── steps/              # Step definitions
│           └── obsidian_parser_steps.py
├── docs/                       # Documentation
├── config.yaml                 # User configuration
├── requirements.txt            # Python dependencies
├── pyproject.toml             # Package metadata
└── .env                       # Environment variables (not in git)
```

## Key Features

1. **Wikilink Conversion**: Converts `[[wikilinks]]` and `[[links|aliases]]` to Notion page mentions
2. **Attachment Handling**: Manages embedded images and files with `![[file]]` syntax
3. **Deduplication**: Prevents creating duplicate pages in Notion
4. **Frontmatter Support**: Migrates YAML frontmatter as Notion properties
5. **Progress Tracking**: Real-time progress bars using tqdm
6. **Dry Run Mode**: Preview changes without modifying Notion

## Development Workflow

### Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -e ".[test]"  # or pip install -e ".[dev]"
```

### Testing
```bash
# Run unit tests
pytest tests/unit/

# Run unit tests with coverage
pytest tests/unit/ --cov=src/obsidian_to_notion --cov-report=term-missing

# Run integration tests
cd tests/integration && behave

# Run specific feature
cd tests/integration && behave features/obsidian_parser.feature

# Run all tests
pytest tests/unit/ && cd tests/integration && behave
```

### Common Commands
```bash
# Basic migration (uses config.yaml)
obsidian-to-notion

# Dry run mode
obsidian-to-notion --dry-run

# Custom config file
obsidian-to-notion --config my-config.yaml

# Override vault path
obsidian-to-notion --vault /path/to/vault

# Verbose logging
obsidian-to-notion --verbose

# Combined options
obsidian-to-notion --vault /path/to/vault --dry-run --verbose
```

## Configuration System

The project uses a dataclass-based configuration system with YAML file support and environment variable overrides.

### Configuration Structure
```yaml
vault:
  path: "/path/to/obsidian/vault"

migration:
  batch_size: 50              # Files per batch
  parallel_workers: 3         # Concurrent workers
  retry_attempts: 3          # API retry count
  skip_duplicates: true      # Skip existing pages
  upload_attachments: true   # Upload embedded files
  max_file_size_mb: 5       # Max attachment size

notion:
  api_url: "https://api.notion.com/v1"
  timeout: 30                          # Request timeout
  rate_limit_requests_per_second: 3    # API rate limit

logging:
  level: "INFO"             # Log level
  progress_bar: true        # Show progress
  log_file: "migration.log" # Log output file
```

### Environment Variables
- `NOTION_TOKEN`: Notion integration token (required)
- `NOTION_DATABASE_ID`: Target database ID (optional)

### CLI Options
- `--config`: Custom config file path (default: config.yaml)
- `--vault`: Override vault path from config
- `--dry-run`: Preview without making changes
- `--verbose`: Enable debug logging

## Architecture Notes

- **Parser**: ObsidianVaultProcessor recursively scans vault directories and extracts:
  - All markdown files with frontmatter metadata
  - Wikilinks in all variations: `[[note]]`, `[[note|alias]]`, `[[note#section]]`, `![[embed]]`
  - Embedded attachments (images, PDFs, documents)
  - Creates a wikilink map for cross-reference resolution
  - Sanitizes text for Notion compatibility
- **Notion Client**: Wrapper around notion-client with retry logic and rate limiting support
- **Config**: Dataclass-based configuration with YAML loading, env var overrides, and validation
- **Error Handling**: Custom exception hierarchy for different error scenarios
- **Progress Tracking**: tqdm-based progress bars with nested support for batch operations

## Implementation Status

### ✅ Completed
- [x] Project structure and package setup
- [x] Dataclass-based configuration system
- [x] YAML configuration loading with validation
- [x] Environment variable overrides
- [x] CLI argument parsing
- [x] Logging system with file output
- [x] ObsidianVaultProcessor implementation:
  - [x] Recursive vault scanning for markdown files and attachments
  - [x] Frontmatter extraction (title, tags, date, custom metadata)
  - [x] Comprehensive wikilink parsing (all Obsidian link formats)
  - [x] Embedded attachment detection
  - [x] Wikilink map creation for cross-references
  - [x] Text sanitization for Notion compatibility
- [x] Notion client wrapper structure
- [x] Error handling framework
- [x] Progress reporting utilities
- [x] Comprehensive test suite for ObsidianVaultProcessor:
  - [x] Unit tests with 100% code coverage
  - [x] BDD integration tests using Behave/Gherkin
  - [x] Tests for all wikilink formats, frontmatter extraction, sanitization
  - [x] Error handling and edge case testing
- [x] NotionMigrationClient implementation:
  - [x] Automatic rate limiting (configurable requests per second)
  - [x] Retry logic with exponential backoff
  - [x] Support for rate limit headers from Notion API
  - [x] Page creation, update, and querying methods
  - [x] Database pagination handling
  - [x] File upload placeholder (needs external storage integration)
- [x] DeduplicationManager implementation:
  - [x] Load and index existing pages from Notion database
  - [x] Case-insensitive duplicate detection
  - [x] Extract titles from various Notion property names
- [x] Comprehensive test suite for Notion client:
  - [x] Unit tests with 100% coverage
  - [x] BDD integration tests for all scenarios
  - [x] Rate limiting, retry, and error handling tests

### 🚧 In Progress
- [ ] Main migration logic implementation
- [ ] Wikilink to Notion page resolution
- [ ] Batch processing implementation

### 📋 TODO
- [ ] File attachment upload (S3/Cloudinary integration)
- [ ] Support for Obsidian plugins syntax
- [ ] Progress persistence for resumable migrations
- [ ] Rollback capability for failed migrations

## Current Limitations

1. **File Uploads**: Notion API doesn't support direct file uploads - needs external hosting
2. **Large Vaults**: Batch configuration exists but processing logic not implemented
3. **Complex Formatting**: Some Obsidian plugins' syntax not supported