"""Unit tests for Notion client module."""

import unittest
from unittest.mock import MagicMock, patch

from notion_client.errors import APIResponseError

from obsidian_to_notion.notion.client import NotionClient


class TestNotionClient(unittest.TestCase):
    """Test NotionClient class."""

    def setUp(self):
        """Set up test fixtures."""
        self.token = "test-token"
        with patch("obsidian_to_notion.notion.client.Client"):
            self.client = NotionClient(self.token)
        self.mock_notion_client = self.client.client

    def test_init(self):
        """Test NotionClient initialization."""
        self.assertIsNotNone(self.client.client)
        self.assertEqual(self.client._page_cache, {})

    def test_search_pages_success(self):
        """Test successful page search."""
        mock_response = {
            "results": [
                {"id": "page1", "properties": {}},
                {"id": "page2", "properties": {}},
            ]
        }
        self.mock_notion_client.search.return_value = mock_response

        results = self.client.search_pages("test query")

        self.assertEqual(len(results), 2)
        self.mock_notion_client.search.assert_called_once_with(
            query="test query", filter={"property": "object", "value": "page"}
        )

    def test_search_pages_error(self):
        """Test page search with API error."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        self.mock_notion_client.search.side_effect = APIResponseError(
            response=mock_response, message="API Error", code="bad_request"
        )

        results = self.client.search_pages("test query")

        self.assertEqual(results, [])

    def test_find_page_by_title_cached(self):
        """Test finding page by title when cached."""
        cached_page = {"id": "page1", "properties": {}}
        self.client._page_cache["Test Page"] = cached_page

        result = self.client.find_page_by_title("Test Page")

        self.assertEqual(result, cached_page)
        # Should not call search since it's cached
        self.mock_notion_client.search.assert_not_called()

    def test_find_page_by_title_found(self):
        """Test finding page by title."""
        mock_page = {
            "id": "page1",
            "properties": {
                "title": {
                    "type": "title",
                    "title": [{"plain_text": "Test Page"}],
                }
            },
        }
        self.mock_notion_client.search.return_value = {"results": [mock_page]}

        result = self.client.find_page_by_title("Test Page")

        self.assertEqual(result, mock_page)
        self.assertIn("Test Page", self.client._page_cache)

    def test_find_page_by_title_not_found(self):
        """Test finding page by title when not found."""
        mock_page = {
            "id": "page1",
            "properties": {
                "title": {
                    "type": "title",
                    "title": [{"plain_text": "Different Page"}],
                }
            },
        }
        self.mock_notion_client.search.return_value = {"results": [mock_page]}

        result = self.client.find_page_by_title("Test Page")

        self.assertIsNone(result)

    def test_get_page_title_standard(self):
        """Test extracting page title from standard property."""
        page = {
            "properties": {
                "title": {
                    "type": "title",
                    "title": [{"plain_text": "Test Title"}],
                }
            }
        }

        title = self.client.get_page_title(page)

        self.assertEqual(title, "Test Title")

    def test_get_page_title_capitalized(self):
        """Test extracting page title from Title property."""
        page = {
            "properties": {
                "Title": {
                    "type": "title",
                    "title": [{"plain_text": "Test Title"}],
                }
            }
        }

        title = self.client.get_page_title(page)

        self.assertEqual(title, "Test Title")

    def test_get_page_title_name(self):
        """Test extracting page title from Name property."""
        page = {
            "properties": {
                "Name": {
                    "type": "title",
                    "title": [{"plain_text": "Test Title"}],
                }
            }
        }

        title = self.client.get_page_title(page)

        self.assertEqual(title, "Test Title")

    def test_get_page_title_empty(self):
        """Test extracting title when no title property exists."""
        page = {"properties": {}}

        title = self.client.get_page_title(page)

        self.assertEqual(title, "")

    def test_get_page_title_empty_array(self):
        """Test extracting title when title array is empty."""
        page = {
            "properties": {
                "title": {
                    "type": "title",
                    "title": [],
                }
            }
        }

        title = self.client.get_page_title(page)

        self.assertEqual(title, "")

    def test_create_page_success(self):
        """Test successful page creation."""
        mock_page = {"id": "new-page", "properties": {}}
        self.mock_notion_client.pages.create.return_value = mock_page

        result = self.client.create_page(
            "parent-id",
            "Test Page",
            [
                {
                    "type": "paragraph",
                    "paragraph": {"text": [{"text": {"content": "Test"}}]},
                }
            ],
            {"tags": {"multi_select": [{"name": "test"}]}},
        )

        self.assertEqual(result, mock_page)
        self.assertIn("Test Page", self.client._page_cache)

    def test_create_page_error(self):
        """Test page creation with API error."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        self.mock_notion_client.pages.create.side_effect = APIResponseError(
            response=mock_response, message="API Error", code="bad_request"
        )

        with self.assertRaises(APIResponseError):
            self.client.create_page(
                "parent-id",
                "Test Page",
                [
                    {
                        "type": "paragraph",
                        "paragraph": {"text": [{"text": {"content": "Test"}}]},
                    }
                ],
            )

    def test_create_page_unexpected_response(self):
        """Test page creation with unexpected response type."""
        # Return a non-dict response
        self.mock_notion_client.pages.create.return_value = "unexpected"

        with self.assertRaises(ValueError) as cm:
            self.client.create_page(
                "parent-id",
                "Test Page",
                [
                    {
                        "type": "paragraph",
                        "paragraph": {"text": [{"text": {"content": "Test"}}]},
                    }
                ],
            )

        self.assertIn("Unexpected response type", str(cm.exception))

    def test_update_page_success(self):
        """Test successful page update."""
        mock_page = {"id": "page-id", "properties": {}}
        self.mock_notion_client.pages.update.return_value = mock_page

        result = self.client.update_page(
            "page-id",
            {"title": {"title": [{"text": {"content": "Updated Title"}}]}},
        )

        self.assertEqual(result, mock_page)

    def test_update_page_error(self):
        """Test page update with API error."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        self.mock_notion_client.pages.update.side_effect = APIResponseError(
            response=mock_response, message="API Error", code="bad_request"
        )

        with self.assertRaises(APIResponseError):
            self.client.update_page("page-id", {})

    def test_update_page_unexpected_response(self):
        """Test page update with unexpected response type."""
        self.mock_notion_client.pages.update.return_value = "unexpected"

        with self.assertRaises(ValueError) as cm:
            self.client.update_page("page-id", {})

        self.assertIn("Unexpected response type", str(cm.exception))

    def test_append_blocks_success(self):
        """Test successful block append."""
        mock_blocks = [{"id": "block1"}, {"id": "block2"}]
        self.mock_notion_client.blocks.children.append.return_value = {
            "results": mock_blocks
        }

        blocks = [
            {
                "type": "paragraph",
                "paragraph": {"text": [{"text": {"content": "Test"}}]},
            }
        ]
        result = self.client.append_blocks("page-id", blocks)

        self.assertEqual(result, mock_blocks)

    def test_append_blocks_error(self):
        """Test block append with API error."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        self.mock_notion_client.blocks.children.append.side_effect = APIResponseError(
            response=mock_response, message="API Error", code="bad_request"
        )

        with self.assertRaises(APIResponseError):
            self.client.append_blocks("page-id", [])

    def test_upload_file_not_implemented(self):
        """Test file upload placeholder."""
        result = self.client.upload_file("/path/to/file.pdf", "page-id")
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
