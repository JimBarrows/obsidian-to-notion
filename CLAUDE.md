# CLAUDE.md - Obsidian to Notion Migration Tool

This file provides project-specific guidance to Claude Code when working with this repository.

## Development Standards Reference
This project follows my universal development standards documented in `~/.claude/CLAUDE.md`.

### Project-Specific Overrides/Extensions
None - this project follows all universal standards without modifications.

## Project Overview
Obsidian to Notion Migration Tool - A Python utility for migrating Obsidian markdown files to Notion with support for wikilink conversion, file attachments, and deduplication.

## Architecture Overview
The tool follows a modular architecture with clear separation of concerns:
- **Parsers**: Handle Obsidian vault processing and markdown parsing
- **Transformers**: Convert Obsidian-specific syntax to Notion-compatible format
- **Notion Client**: Manages API interactions with rate limiting and retry logic
- **Migration Orchestrator**: Coordinates the entire migration process
- **Configuration**: Dataclass-based config with YAML support and env var overrides

### Technology Stack
- Python 3.8+
- notion-client: Official Notion API client
- pyyaml: YAML configuration parsing
- tqdm: Progress bar display
- pytest: Unit testing framework
- behave: BDD testing framework
- black, isort, flake8, mypy, ruff: Code quality tools

### Project Structure
```
obsidian-to-notion/
├── src/obsidian_to_notion/     # Main package
│   ├── main.py                 # Migration orchestrator and CLI entry
│   ├── config.py               # Configuration management
│   ├── parsers/                # Obsidian parsing modules
│   │   └── obsidian_parser.py  # Markdown and wikilink parser
│   ├── notion/                 # Notion API integration
│   │   ├── client.py           # Notion API wrapper with rate limiting
│   │   └── deduplication.py    # Duplicate detection
│   ├── transformers/           # Content transformation
│   │   └── wikilink_converter.py # Convert Obsidian links to Notion
│   └── utils/                  # Utility modules
│       ├── progress.py         # Progress reporting
│       └── error_handling.py   # Error handling utilities
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests
│   └── integration/            # BDD integration tests
│       ├── features/           # Gherkin feature files
│       └── steps/              # Step definitions
├── migrate.py                  # Simple CLI entry point
├── config.yaml                 # User configuration
├── requirements.txt            # Python dependencies
├── pyproject.toml             # Package metadata
└── .env                       # Environment variables (not in git)
```

## Project-Specific Commands

### Environment Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install for development
pip install -e ".[dev]"

# Install for testing only
pip install -e ".[test]"
```

### Build and Test
```bash
# Run all tests
pytest tests/unit/ && cd tests/integration && behave

# Unit tests with coverage
pytest tests/unit/ --cov=src/obsidian_to_notion --cov-report=term-missing

# Integration tests only
cd tests/integration && behave

# Specific feature test
cd tests/integration && behave features/obsidian_parser.feature

# Code quality checks
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
```

### Deployment
```bash
# Build distribution
python -m build

# Install from PyPI (when published)
pip install obsidian-to-notion

# Run migration
obsidian-to-notion --config config.yaml
```

## Configuration
The tool uses a hierarchical configuration system:
1. Default values in dataclasses
2. YAML configuration file
3. Environment variable overrides
4. CLI argument overrides

### Required Environment Variables
- `NOTION_TOKEN`: Notion integration token (required)
- `NOTION_DATABASE_ID`: Target database ID (can be in config.yaml)

### Configuration File (config.yaml)
```yaml
vault:
  path: "/path/to/obsidian/vault"

migration:
  batch_size: 50
  parallel_workers: 3
  retry_attempts: 3
  skip_duplicates: true
  upload_attachments: true
  max_file_size_mb: 5

notion:
  database_id: "your-database-id"  # Can override with env var
  rate_limit_requests_per_second: 3

logging:
  level: "INFO"
  progress_bar: true
  log_file: "migration.log"
```

## Testing Approach
Beyond the universal TDD standards:
- BDD scenarios cover end-to-end migration workflows
- Unit tests achieve 100% code coverage
- Integration tests verify Notion API interactions
- All wikilink formats are tested comprehensively
- Error scenarios are thoroughly covered

## Current Implementation Status
- [x] Core architecture and configuration system
- [x] Obsidian vault parsing with wikilink extraction
- [x] Notion API client with rate limiting
- [x] Deduplication management
- [x] Main migration orchestrator
- [ ] Wikilink to Notion page resolution
- [ ] Batch processing for large vaults
- [ ] File attachment upload integration
- [ ] Progress persistence for resumable migrations

## Troubleshooting
### Common Issues

1. **Import Sorting Conflicts**
   - isort and ruff may have different requirements
   - Solution: Use ruff's format as it's the final check

2. **Pre-commit Hook Failures**
   - Run `pre-commit run --all-files` to see all issues
   - For persistent issues, fix manually or use `--no-verify` flag

3. **Notion API Rate Limits**
   - Default is 3 requests/second
   - Adjust `rate_limit_requests_per_second` in config if needed

4. **Large Vault Processing**
   - Use batch_size configuration to control memory usage
   - Enable progress_bar to monitor progress

---

**Note**: For universal development workflow, see `~/.claude/CLAUDE.md`. Use the command `/start-feature {issue-number}` to begin feature development following standard workflow.
