# Obsidian to Notion Migration Tool

A Python utility for migrating Obsidian markdown files to Notion, with support for wikilink conversion, file attachments, and deduplication.

## Features

- **Wikilink Conversion**: Automatically converts Obsidian `[[wikilinks]]` to Notion page mentions
- **Attachment Handling**: Manages embedded images and file attachments
- **Deduplication**: Prevents creating duplicate pages in Notion
- **Frontmatter Support**: Migrates YAML frontmatter as Notion page properties
- **Folder Structure**: Optionally preserves Obsidian folder hierarchy as nested Notion pages
- **Progress Tracking**: Real-time progress bars for large vault migrations
- **Dry Run Mode**: Preview changes without modifying your Notion workspace

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/obsidian-to-notion.git
cd obsidian-to-notion
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

1. Copy the environment example file and add your Notion credentials:
```bash
cp .env.example .env
```

2. Edit `.env` and add your Notion integration token:
```
NOTION_TOKEN=your_notion_integration_token_here
```

3. Get your Notion integration token:
   - Go to https://www.notion.so/my-integrations
   - Create a new integration
   - Copy the "Internal Integration Token"
   - Share your target Notion page with the integration

4. Customize `config.yaml` for your migration preferences

## Usage

Basic usage:
```bash
python -m obsidian_to_notion.main /path/to/obsidian/vault
```

With custom config:
```bash
python -m obsidian_to_notion.main /path/to/obsidian/vault --config my-config.yaml
```

Dry run (preview without uploading):
```bash
python -m obsidian_to_notion.main /path/to/obsidian/vault --dry-run
```

Verbose logging:
```bash
python -m obsidian_to_notion.main /path/to/obsidian/vault --verbose
```

## Configuration Options

See `config.yaml.example` for all available options:

- **Skip Patterns**: Exclude certain folders or files from migration
- **Duplicate Handling**: Choose how to handle existing pages (skip, update, or create new)
- **Folder Structure**: Preserve or flatten your vault's organization
- **Attachment Extensions**: Specify which file types to treat as attachments

## Limitations

- **File Attachments**: The Notion API doesn't directly support file uploads. Attachments need to be hosted externally (e.g., S3, Cloudinary) and linked
- **Complex Formatting**: Some Obsidian-specific syntax may not translate perfectly to Notion's block format
- **Large Vaults**: Very large vaults may take time due to API rate limits

## Development

To set up for development:

```bash
pip install -e ".[dev]"
pre-commit install
```

Run tests:
```bash
pytest
```

## License

MIT License - see LICENSE file for details