"""Convert Obsidian wikilinks to Notion links."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple


class WikilinkConverter:
    """Convert Obsidian wikilinks to Notion-compatible links."""

    def __init__(self, page_mapping: Dict[str, str]):
        """Initialize converter with page mapping.

        Args:
            page_mapping: Dictionary mapping Obsidian file paths to Notion page IDs
        """
        self.page_mapping = page_mapping

    def convert_content(
        self, content: str, links: List[Tuple[str, str]], current_file: Path
    ) -> str:
        """Convert wikilinks in content to Notion links.

        Args:
            content: Original markdown content
            links: List of (full_match, link_text) tuples
            current_file: Path of the current file being processed

        Returns:
            Content with converted links
        """
        converted = content

        for full_match, link_text in links:
            notion_link = self.convert_wikilink(link_text, current_file)
            if notion_link:
                converted = converted.replace(full_match, notion_link)

        return converted

    def convert_wikilink(self, link_text: str, current_file: Path) -> Optional[str]:
        """Convert a single wikilink to Notion format.

        Args:
            link_text: Text inside the wikilink
            current_file: Path of the file containing the link

        Returns:
            Notion-formatted link or None if target not found
        """
        # Parse link components
        alias = None
        section = None

        # Handle aliases
        if "|" in link_text:
            link_path, alias = link_text.split("|", 1)
        else:
            link_path = link_text

        # Handle section links
        if "#" in link_path:
            parts = link_path.split("#", 1)
            link_path = parts[0]
            section = parts[1] if len(parts) > 1 else None

        # Determine display text
        display_text = alias or link_path or current_file.stem

        # If it's a same-file section link
        if not link_path:
            # For now, just return the display text
            # TODO: Handle section anchors when Notion API supports them
            return f"[{display_text}](#{section})" if section else display_text

        # Look up Notion page ID
        notion_page_id = self.page_mapping.get(link_path)
        if not notion_page_id:
            # Return as plain text if page not found
            return f"{display_text} (page not found)"

        # Format as Notion mention
        return self.format_notion_mention(notion_page_id, display_text)

    def format_notion_mention(self, page_id: str, display_text: str) -> str:
        """Format a Notion page mention.

        Args:
            page_id: Notion page ID
            display_text: Text to display

        Returns:
            Formatted mention
        """
        # Notion uses a special format for page mentions in markdown
        # For API, we'll need to use block format
        return f"[{display_text}](notion://www.notion.so/{page_id.replace('-', '')})"

    def create_mention_block(self, page_id: str) -> Dict:
        """Create a Notion mention block.

        Args:
            page_id: Notion page ID to mention

        Returns:
            Notion block object
        """
        return {
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "mention",
                        "mention": {"type": "page", "page": {"id": page_id}},
                    }
                ]
            },
        }
