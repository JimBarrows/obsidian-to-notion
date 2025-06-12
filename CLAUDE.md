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
pip install -e ".[dev]"
```

### Testing
```bash
# Run with test vault
obsidian-to-notion test_vault --dry-run --verbose

# Run tests (when implemented)
pytest
```

### Common Commands
```bash
# Basic migration
obsidian-to-notion /path/to/vault

# Dry run
obsidian-to-notion /path/to/vault --dry-run

# Custom config
obsidian-to-notion /path/to/vault --config my-config.yaml
```

## Architecture Notes

- **Parser**: Uses regex patterns to extract wikilinks, embeds, and tags
- **Notion Client**: Wrapper around notion-client with retry logic
- **Config**: Hierarchical configuration with env var overrides
- **Error Handling**: Custom exception types for different error scenarios

## Current Limitations

1. **File Uploads**: Notion API doesn't support direct file uploads - needs external hosting
2. **Rate Limiting**: No rate limiting implemented yet
3. **Large Vaults**: No batching for very large vaults
4. **Complex Formatting**: Some Obsidian plugins' syntax not supported

## TODO

- [ ] Implement actual migration logic in main.py
- [ ] Add rate limiting for Notion API
- [ ] Implement file hosting integration (S3/Cloudinary)
- [ ] Add comprehensive test suite
- [ ] Support for Obsidian plugins syntax
- [ ] Progress persistence for resumable migrations