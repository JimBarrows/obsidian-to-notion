"""Convert Obsidian wikilinks to Notion links."""

import logging
import re
from typing import Any, Dict, List, Optional

from ..utils.error_handling import (
    create_error_context,
    log_error_with_context,
)


class WikilinkConverter:
    """Convert Obsidian wikilinks to Notion-compatible links.

    This class provides functionality to convert Obsidian-style wikilinks
    ([[page]] and [[page|alias]]) to Notion page mentions or fallback text.
    """

    def __init__(self, page_mapping: Optional[Dict[str, str]] = None) -> None:
        """Initialize WikilinkConverter with optional page mapping.

        Args:
            page_mapping: Dictionary mapping page titles to Notion page IDs
        """
        self.page_mapping: Dict[str, str] = page_mapping or {}
        self.page_cache: Dict[str, str] = {}
        self.broken_links: List[str] = []
        self.logger = logging.getLogger(__name__)

    def add_page_to_cache(self, title: str, page_id: str) -> None:
        """Add a page to the cache for link resolution.

        Args:
            title: Page title
            page_id: Notion page ID
        """
        normalized_title = title.lower().strip()
        self.page_cache[normalized_title] = page_id
        self.page_mapping[title] = page_id

    def convert_content(self, content: str, wikilinks: List[Dict[str, Any]]) -> str:
        """Convert wikilinks in content to Notion links.

        Args:
            content: Original markdown content
            wikilinks: List of wikilink dictionaries with 'note_name' and optional
                'alias'

        Returns:
            Content with converted links
        """
        converted_content = content

        for index, link_info in enumerate(wikilinks):
            note_name = link_info.get("note_name", "")
            alias = link_info.get("alias")
            section = link_info.get("section")

            if not note_name:
                context = create_error_context(
                    phase="wikilink_conversion",
                    wikilink_index=index,
                    wikilink_info=link_info,
                    error_type="EmptyNoteName",
                )
                self.logger.warning(
                    "Skipping wikilink with empty note_name", extra=context
                )
                continue

            try:
                # Find the original wikilink pattern in content
                original_link = self._find_original_link(
                    content, note_name, alias, section
                )
                if not original_link:
                    context = create_error_context(
                        phase="wikilink_conversion",
                        note_name=note_name,
                        alias=alias,
                        section=section,
                        wikilink_index=index,
                        error_type="WikilinkNotFound",
                    )
                    self.logger.warning(
                        f"Could not find original wikilink pattern for: {note_name}",
                        extra=context,
                    )
                    continue

                # Convert to Notion format
                notion_link = self._convert_wikilink_to_notion(
                    note_name, alias, section
                )

                # Replace in content
                converted_content = converted_content.replace(
                    original_link, notion_link
                )

            except Exception as e:
                context = create_error_context(
                    phase="wikilink_conversion",
                    note_name=note_name,
                    alias=alias,
                    section=section,
                    original_link=(
                        original_link if "original_link" in locals() else None
                    ),
                    wikilink_index=index,
                    error_type=type(e).__name__,
                )
                log_error_with_context(self.logger, e, context)
                # Continue with other links even if one fails
                continue

        return converted_content

    def _find_original_link(
        self,
        content: str,
        note_name: str,
        alias: Optional[str] = None,
        section: Optional[str] = None,
    ) -> Optional[str]:
        """Find the original wikilink pattern in content.

        Args:
            content: Content to search in
            note_name: Note name from wikilink
            alias: Optional alias
            section: Optional section reference

        Returns:
            Original wikilink string if found
        """
        # Build possible patterns
        patterns = []

        if alias:
            if section:
                patterns.append(f"[[{note_name}#{section}|{alias}]]")
            patterns.append(f"[[{note_name}|{alias}]]")

        if section:
            patterns.append(f"[[{note_name}#{section}]]")

        patterns.append(f"[[{note_name}]]")

        # Check each pattern
        for pattern in patterns:
            if pattern in content:
                return pattern

        return None

    def _convert_wikilink_to_notion(
        self, note_name: str, alias: Optional[str] = None, section: Optional[str] = None
    ) -> str:
        """Convert a single wikilink to Notion format.

        Args:
            note_name: Name of the note being linked to
            alias: Optional display alias
            section: Optional section reference

        Returns:
            Notion-formatted link or fallback text
        """
        normalized_name = note_name.lower().strip()
        display_text = alias or note_name

        # Add section to display text if present
        if section and not alias:
            display_text = f"{note_name}#{section}"
        elif section and alias:
            display_text = f"{alias} (#{section})"

        # Check if we have a Notion page ID for this note
        page_id = self.page_cache.get(normalized_name) or self.page_mapping.get(
            note_name
        )

        if page_id:
            # Create Notion page mention link
            # Note: This creates a markdown link that can be converted to Notion blocks
            return f"[{display_text}](@{page_id})"
        else:
            # Track broken link
            broken_link = f"{note_name}#{section}" if section else note_name
            if broken_link not in self.broken_links:
                self.broken_links.append(broken_link)

            # Return as plain text with indicator
            return f"{display_text} (link not found)"

    def get_broken_links_report(self) -> str:
        """Get report of broken links found during conversion.

        Returns:
            Human-readable report of broken links
        """
        if not self.broken_links:
            return "No broken links found"

        report_lines = [f"Found {len(self.broken_links)} broken links:", ""]

        for link in sorted(set(self.broken_links)):
            report_lines.append(f"  - {link}")

        return "\n".join(report_lines)

    def create_mention_rich_text(
        self, page_id: str, display_text: str
    ) -> Dict[str, Any]:
        """Create a Notion rich text mention object.

        Args:
            page_id: Notion page ID to mention
            display_text: Text to display for the mention

        Returns:
            Notion rich text mention object
        """
        return {
            "type": "mention",
            "mention": {"type": "page", "page": {"id": page_id}},
            "annotations": {
                "bold": False,
                "italic": False,
                "strikethrough": False,
                "underline": False,
                "code": False,
                "color": "default",
            },
            "plain_text": display_text,
            "href": f"https://www.notion.so/{page_id.replace('-', '')}",
        }

    def parse_notion_link_from_content(self, content: str) -> List[Dict[str, Any]]:
        """Parse converted Notion links from content to create rich text objects.

        Args:
            content: Content containing converted Notion links

        Returns:
            List of rich text objects for Notion API
        """
        rich_text = []

        # Pattern to match our converted links: [display_text](@page_id)
        link_pattern = r"\[([^\]]+)\]\(@([^)]+)\)"

        last_end = 0

        try:
            for match_index, match in enumerate(re.finditer(link_pattern, content)):
                start, end = match.span()
                display_text = match.group(1)
                page_id = match.group(2)

                # Add text before the link
                if start > last_end:
                    text_before = content[last_end:start]
                    if text_before:
                        rich_text.append(
                            {"type": "text", "text": {"content": text_before}}
                        )

                # Add the mention
                try:
                    rich_text.append(
                        self.create_mention_rich_text(page_id, display_text)
                    )
                except Exception as e:
                    context = create_error_context(
                        phase="notion_link_parsing",
                        display_text=display_text,
                        page_id=page_id,
                        match_index=match_index,
                        match_position=start,
                        error_type=type(e).__name__,
                    )
                    log_error_with_context(self.logger, e, context)
                    # Fall back to plain text
                    rich_text.append(
                        {"type": "text", "text": {"content": f"[{display_text}]"}}
                    )

                last_end = end

            # Add remaining text
            if last_end < len(content):
                remaining_text = content[last_end:]
                if remaining_text:
                    rich_text.append(
                        {"type": "text", "text": {"content": remaining_text}}
                    )

            # If no links found, return the whole content as text
            if not rich_text:
                rich_text = [{"type": "text", "text": {"content": content}}]

        except Exception as e:
            context = create_error_context(
                phase="notion_link_parsing",
                content_length=len(content),
                error_type=type(e).__name__,
            )
            log_error_with_context(self.logger, e, context)
            # Fall back to plain text
            rich_text = [{"type": "text", "text": {"content": content}}]

        return rich_text
