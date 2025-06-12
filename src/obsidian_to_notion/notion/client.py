"""Notion API client wrapper."""

import logging
from typing import Dict, List, Optional

from notion_client import Client
from notion_client.errors import APIResponseError

logger = logging.getLogger(__name__)


class NotionClient:
    """Wrapper for Notion API client with helper methods."""

    def __init__(self, token: str):
        """Initialize Notion client.

        Args:
            token: Notion integration token
        """
        self.client = Client(auth=token)
        self._page_cache: Dict[str, Dict] = {}

    def search_pages(self, query: str) -> List[Dict]:
        """Search for pages by title.

        Args:
            query: Search query

        Returns:
            List of matching pages
        """
        try:
            response = self.client.search(
                query=query, filter={"property": "object", "value": "page"}
            )
            return response.get("results", [])  # type: ignore[no-any-return,union-attr]
        except APIResponseError as e:
            logger.error(f"Failed to search pages: {e}")
            return []

    def find_page_by_title(self, title: str) -> Optional[Dict]:
        """Find a page by exact title match.

        Args:
            title: Page title to search for

        Returns:
            Page object or None if not found
        """
        # Check cache first
        if title in self._page_cache:
            return self._page_cache[title]

        pages = self.search_pages(title)
        for page in pages:
            page_title = self.get_page_title(page)
            if page_title == title:
                self._page_cache[title] = page
                return page

        return None

    def get_page_title(self, page: Dict) -> str:
        """Extract title from a page object.

        Args:
            page: Notion page object

        Returns:
            Page title
        """
        properties = page.get("properties", {})

        # Try common title property names
        for prop_name in ["title", "Title", "Name"]:
            if prop_name in properties:
                title_prop = properties[prop_name]
                if title_prop.get("type") == "title":
                    title_array = title_prop.get("title", [])
                    if title_array:
                        # type: ignore[no-any-return]
                        return title_array[0].get("plain_text", "")

        return ""

    def create_page(
        self,
        parent_id: str,
        title: str,
        content: List[Dict],
        properties: Optional[Dict] = None,
    ) -> Dict:
        """Create a new page in Notion.

        Args:
            parent_id: Parent page or database ID
            title: Page title
            content: List of block objects
            properties: Additional page properties

        Returns:
            Created page object
        """
        page_data = {
            "parent": {"page_id": parent_id},
            "properties": properties or {},
            "children": content,
        }

        # Set title property
        props = page_data.get("properties", {})
        props["title"] = {"title": [{"text": {"content": title}}]}
        page_data["properties"] = props  # type: ignore[index]

        try:
            page = self.client.pages.create(**page_data)
            self._page_cache[title] = page
            logger.info(f"Created page: {title}")
            return page  # type: ignore[no-any-return,return-value,assignment]
        except APIResponseError as e:
            logger.error(f"Failed to create page '{title}': {e}")
            raise

    def update_page(self, page_id: str, properties: Dict) -> Dict:
        """Update page properties.

        Args:
            page_id: Page ID to update
            properties: Properties to update

        Returns:
            Updated page object
        """
        try:
            # type: ignore[no-any-return,return-value]
            return self.client.pages.update(page_id=page_id, properties=properties)
        except APIResponseError as e:
            logger.error(f"Failed to update page {page_id}: {e}")
            raise

    def append_blocks(self, page_id: str, blocks: List[Dict]) -> List[Dict]:
        """Append blocks to a page.

        Args:
            page_id: Page ID to append to
            blocks: List of block objects

        Returns:
            Created blocks
        """
        try:
            response = self.client.blocks.children.append(
                block_id=page_id, children=blocks
            )
            return response.get("results", [])  # type: ignore[no-any-return,union-attr]
        except APIResponseError as e:
            logger.error(f"Failed to append blocks to {page_id}: {e}")
            raise

    def upload_file(self, file_path: str, page_id: str) -> str:
        """Upload a file to Notion.

        Note: Notion API doesn't directly support file uploads.
        Files need to be hosted externally and linked.

        Args:
            file_path: Path to file
            page_id: Page to attach file to

        Returns:
            URL of uploaded file
        """
        # TODO: Implement file hosting solution
        logger.warning(f"File upload not implemented: {file_path}")
        return ""
