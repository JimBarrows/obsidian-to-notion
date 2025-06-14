# Obsidian to Notion Migration Tool

A Python utility to migrate Obsidian markdown files to Notion databases, handling wikilinks, attachments, and deduplication.

## Setup

1. Clone/download this project
2. Create virtual environment: `python -m venv .venv`
3. Activate it: `source .venv/bin/activate` (Linux/Mac) or `.venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and fill in your Notion API credentials
6. Update `config.yaml` with your Obsidian vault path

## Usage

```bash
# Dry run to see what would be migrated
python migrate.py --dry-run

# Actual migration
python migrate.py

# Custom config file
python migrate.py --config my-config.yaml
```

## Configuration

Edit config.yaml to customize:

- Vault path
- Migration settings (batch size, retries, etc.)
- Notion API settings
- Logging preferences

## Environment Variables

Required in .env file:

- NOTION_TOKEN: Your Notion integration token
- NOTION_DATABASE_ID: Target Notion database ID

## Features

✅ Wikilink conversion
✅ Deduplication by title
✅ Progress tracking
✅ Error handling and retries
✅ Rate limiting for Notion API
✅ Dry run mode
✅ Comprehensive logging
