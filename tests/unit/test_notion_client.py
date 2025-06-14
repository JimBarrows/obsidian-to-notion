"""Unit tests for Notion API client."""

import time
from unittest.mock import Mock, call, patch

import pytest
from notion_client import APIResponseError

from obsidian_to_notion.notion import DeduplicationManager, NotionMigrationClient


class TestNotionMigrationClient:
    """Test cases for NotionMigrationClient."""

    @patch("obsidian_to_notion.notion.client.Client")
    def test_init_with_default_rate_limit(self, mock_client_class):
        """Test client initialization with default rate limit."""
        client = NotionMigrationClient("test-token")

        assert client.rate_limit_rps == 3
        assert client.request_timestamps == []
        mock_client_class.assert_called_once_with(auth="test-token")

    @patch("obsidian_to_notion.notion.client.Client")
    def test_init_with_custom_rate_limit(self, mock_client_class):
        """Test client initialization with custom rate limit."""
        client = NotionMigrationClient("test-token", rate_limit_rps=5)

        assert client.rate_limit_rps == 5
        assert client.request_timestamps == []

    @patch("obsidian_to_notion.notion.client.Client")
    def test_rate_limited_request_success(self, mock_client_class):
        """Test successful rate-limited request."""
        client = NotionMigrationClient("test-token")
        mock_method = Mock(return_value={"id": "test-id"})

        result = client.rate_limited_request(mock_method, test_param="value")

        assert result == {"id": "test-id"}
        mock_method.assert_called_once_with(test_param="value")
        assert len(client.request_timestamps) == 1

    @patch("obsidian_to_notion.notion.client.Client")
    @patch("time.sleep")
    def test_rate_limiting_enforcement(self, mock_sleep, mock_client_class):
        """Test that rate limiting is enforced."""
        client = NotionMigrationClient("test-token", rate_limit_rps=2)
        mock_method = Mock(return_value={"id": "test-id"})

        # Pre-fill timestamps to simulate hitting rate limit
        current_time = time.time()
        client.request_timestamps = [current_time - 0.5, current_time - 0.3]

        client.rate_limited_request(mock_method)

        # Should have slept to respect rate limit
        mock_sleep.assert_called_once()
        sleep_time = mock_sleep.call_args[0][0]
        assert 0 < sleep_time <= 1.0

    @patch("obsidian_to_notion.notion.client.Client")
    @patch("time.sleep")
    def test_retry_on_api_error(self, mock_sleep, mock_client_class):
        """Test retry mechanism on API errors."""
        client = NotionMigrationClient("test-token")

        # Mock method that fails once then succeeds
        response_mock = Mock()
        response_mock.status_code = 500
        error = APIResponseError(response_mock, "Server Error", "server_error")

        mock_method = Mock(side_effect=[error, {"id": "success-id"}])

        result = client.rate_limited_request(mock_method)

        assert result == {"id": "success-id"}
        assert mock_method.call_count == 2
        mock_sleep.assert_called_once_with(1)  # First retry waits 2^0 = 1 second

    @patch("obsidian_to_notion.notion.client.Client")
    @patch("time.sleep")
    def test_rate_limit_error_handling(self, mock_sleep, mock_client_class):
        """Test handling of rate limit errors from API."""
        client = NotionMigrationClient("test-token")

        # Mock rate limit error with retry-after header
        response_mock = Mock()
        response_mock.status_code = 429
        response_mock.headers = {"retry-after": "2"}
        error = APIResponseError(response_mock, "Rate Limited", "rate_limited")

        mock_method = Mock(side_effect=[error, {"id": "success-id"}])

        result = client.rate_limited_request(mock_method)

        assert result == {"id": "success-id"}
        assert mock_method.call_count == 2
        mock_sleep.assert_called_once_with(2)  # Should wait retry-after seconds

    @patch("obsidian_to_notion.notion.client.Client")
    def test_max_retries_exceeded(self, mock_client_class):
        """Test that errors are raised after max retries."""
        client = NotionMigrationClient("test-token")

        response_mock = Mock()
        response_mock.status_code = 500
        error = APIResponseError(response_mock, "Server Error", "server_error")

        mock_method = Mock(side_effect=error)

        with pytest.raises(APIResponseError):
            client.rate_limited_request(mock_method)

        assert mock_method.call_count == 3  # Initial + 2 retries

    @patch("obsidian_to_notion.notion.client.Client")
    def test_create_page(self, mock_client_class):
        """Test page creation."""
        client = NotionMigrationClient("test-token")
        client.client.pages.create = Mock(return_value={"id": "new-page-id"})

        properties = {"Title": {"title": [{"text": {"content": "Test"}}]}}
        children = [
            {"type": "paragraph", "paragraph": {"text": [{"content": "Content"}]}}
        ]

        result = client.create_page("db-id", properties, children)

        assert result == {"id": "new-page-id"}
        client.client.pages.create.assert_called_once_with(
            parent={"database_id": "db-id"}, properties=properties, children=children
        )

    @patch("obsidian_to_notion.notion.client.Client")
    def test_create_page_without_children(self, mock_client_class):
        """Test page creation without children."""
        client = NotionMigrationClient("test-token")
        client.client.pages.create = Mock(return_value={"id": "new-page-id"})

        properties = {"Title": {"title": [{"text": {"content": "Test"}}]}}

        result = client.create_page("db-id", properties)

        assert result == {"id": "new-page-id"}
        client.client.pages.create.assert_called_once_with(
            parent={"database_id": "db-id"}, properties=properties, children=[]
        )

    @patch("obsidian_to_notion.notion.client.Client")
    def test_update_page_properties(self, mock_client_class):
        """Test updating page properties."""
        client = NotionMigrationClient("test-token")
        client.client.pages.update = Mock(
            return_value={"id": "page-id", "updated": True}
        )

        properties = {"Title": {"title": [{"text": {"content": "Updated"}}]}}

        result = client.update_page("page-id", properties=properties)

        assert result == {"id": "page-id", "updated": True}
        client.client.pages.update.assert_called_once_with(
            page_id="page-id", properties=properties
        )

    @patch("obsidian_to_notion.notion.client.Client")
    def test_update_page_children(self, mock_client_class):
        """Test updating page children."""
        client = NotionMigrationClient("test-token")
        client.client.blocks.children.append = Mock(return_value={"id": "block-id"})

        children = [
            {"type": "paragraph", "paragraph": {"text": [{"content": "New content"}]}}
        ]

        result = client.update_page("page-id", children=children)

        assert result == {"id": "page-id"}
        client.client.blocks.children.append.assert_called_once_with(
            block_id="page-id", children=children
        )

    @patch("obsidian_to_notion.notion.client.Client")
    def test_query_database_simple(self, mock_client_class):
        """Test simple database query."""
        client = NotionMigrationClient("test-token")

        mock_response = {
            "results": [{"id": "page-1"}, {"id": "page-2"}],
            "has_more": False,
        }
        client.client.databases.query = Mock(return_value=mock_response)

        results = client.query_database("db-id")

        assert len(results) == 2
        assert results[0]["id"] == "page-1"
        assert results[1]["id"] == "page-2"
        client.client.databases.query.assert_called_once_with(database_id="db-id")

    @patch("obsidian_to_notion.notion.client.Client")
    def test_query_database_with_filter(self, mock_client_class):
        """Test database query with filter."""
        client = NotionMigrationClient("test-token")

        mock_response = {"results": [{"id": "filtered-page"}], "has_more": False}
        client.client.databases.query = Mock(return_value=mock_response)

        filter_query = {"property": "Status", "select": {"equals": "Active"}}
        results = client.query_database("db-id", filter_query)

        assert len(results) == 1
        assert results[0]["id"] == "filtered-page"
        client.client.databases.query.assert_called_once_with(
            database_id="db-id", filter=filter_query
        )

    @patch("obsidian_to_notion.notion.client.Client")
    def test_query_database_with_pagination(self, mock_client_class):
        """Test database query with pagination."""
        client = NotionMigrationClient("test-token")

        # Mock paginated responses
        responses = [
            {
                "results": [{"id": "page-1"}, {"id": "page-2"}],
                "has_more": True,
                "next_cursor": "cursor-1",
            },
            {"results": [{"id": "page-3"}], "has_more": False},
        ]
        client.client.databases.query = Mock(side_effect=responses)

        results = client.query_database("db-id")

        assert len(results) == 3
        assert results[0]["id"] == "page-1"
        assert results[1]["id"] == "page-2"
        assert results[2]["id"] == "page-3"

        # Verify pagination calls
        calls = client.client.databases.query.call_args_list
        assert len(calls) == 2
        assert calls[0] == call(database_id="db-id")
        assert calls[1] == call(database_id="db-id", start_cursor="cursor-1")

    @patch("obsidian_to_notion.notion.client.Client")
    def test_upload_file_not_implemented(self, mock_client_class):
        """Test file upload returns None (not implemented)."""
        client = NotionMigrationClient("test-token")

        result = client.upload_file("/path/to/file.png")

        assert result is None


class TestDeduplicationManager:
    """Test cases for DeduplicationManager."""

    @patch("obsidian_to_notion.notion.client.Client")
    def test_init(self, mock_client_class):
        """Test deduplication manager initialization."""
        notion_client = NotionMigrationClient("test-token")
        dedup = DeduplicationManager(notion_client, "db-id")

        assert dedup.notion == notion_client
        assert dedup.database_id == "db-id"
        assert dedup.existing_pages == {}

    @patch("obsidian_to_notion.notion.client.Client")
    def test_load_existing_pages(self, mock_client_class):
        """Test loading existing pages from database."""
        notion_client = NotionMigrationClient("test-token")
        notion_client.query_database = Mock(
            return_value=[
                {
                    "id": "page-1",
                    "properties": {
                        "Name": {
                            "type": "title",
                            "title": [{"text": {"content": "Page One"}}],
                        }
                    },
                },
                {
                    "id": "page-2",
                    "properties": {
                        "Title": {
                            "type": "title",
                            "title": [{"text": {"content": "Page Two"}}],
                        }
                    },
                },
            ]
        )

        dedup = DeduplicationManager(notion_client, "db-id")
        dedup.load_existing_pages()

        assert len(dedup.existing_pages) == 2
        assert dedup.existing_pages["page one"] == "page-1"
        assert dedup.existing_pages["page two"] == "page-2"

    @patch("obsidian_to_notion.notion.client.Client")
    def test_should_skip_page_exists(self, mock_client_class):
        """Test checking if page should be skipped (exists)."""
        notion_client = NotionMigrationClient("test-token")
        dedup = DeduplicationManager(notion_client, "db-id")
        dedup.existing_pages = {"test page": "test-id"}

        assert dedup.should_skip_page("Test Page") is True
        assert dedup.should_skip_page("TEST PAGE") is True
        assert dedup.should_skip_page("test page") is True

    @patch("obsidian_to_notion.notion.client.Client")
    def test_should_skip_page_not_exists(self, mock_client_class):
        """Test checking if page should be skipped (doesn't exist)."""
        notion_client = NotionMigrationClient("test-token")
        dedup = DeduplicationManager(notion_client, "db-id")
        dedup.existing_pages = {"test page": "test-id"}

        assert dedup.should_skip_page("New Page") is False
        assert dedup.should_skip_page("Another Page") is False

    @patch("obsidian_to_notion.notion.client.Client")
    def test_get_existing_page_id(self, mock_client_class):
        """Test getting existing page ID."""
        notion_client = NotionMigrationClient("test-token")
        dedup = DeduplicationManager(notion_client, "db-id")
        dedup.existing_pages = {"test page": "test-id-123"}

        assert dedup.get_existing_page_id("Test Page") == "test-id-123"
        assert dedup.get_existing_page_id("TEST PAGE") == "test-id-123"
        assert dedup.get_existing_page_id("New Page") is None

    @patch("obsidian_to_notion.notion.client.Client")
    def test_extract_title_various_properties(self, mock_client_class):
        """Test extracting title from various property names."""
        notion_client = NotionMigrationClient("test-token")
        dedup = DeduplicationManager(notion_client, "db-id")

        # Test with 'Name' property
        page1 = {
            "properties": {
                "Name": {"type": "title", "title": [{"text": {"content": "Test Name"}}]}
            }
        }
        assert dedup.extract_title(page1) == "Test Name"

        # Test with 'Title' property
        page2 = {
            "properties": {
                "Title": {
                    "type": "title",
                    "title": [{"text": {"content": "Test Title"}}],
                }
            }
        }
        assert dedup.extract_title(page2) == "Test Title"

        # Test with lowercase 'title' property
        page3 = {
            "properties": {
                "title": {
                    "type": "title",
                    "title": [{"text": {"content": "Test title"}}],
                }
            }
        }
        assert dedup.extract_title(page3) == "Test title"

        # Test with no title property
        page4 = {
            "properties": {"Status": {"type": "select", "select": {"name": "Active"}}}
        }
        assert dedup.extract_title(page4) is None

        # Test with empty title
        page5 = {"properties": {"Name": {"type": "title", "title": []}}}
        assert dedup.extract_title(page5) is None

    @patch("obsidian_to_notion.notion.client.Client")
    def test_database_not_found_error(self, mock_client_class):
        """Test handling of database not found error."""
        client = NotionMigrationClient("test-token")

        # Mock database not found error
        response_mock = Mock()
        response_mock.status_code = 404
        error = APIResponseError(
            response_mock,
            "Could not find database with ID: f5d6edd0-da90-4e24-9f2f-fdddee9866d8",
            "object_not_found",
        )
        client.client.pages.create = Mock(side_effect=error)

        # Attempt to create a page should raise the error
        with pytest.raises(APIResponseError) as exc_info:
            client.create_page("f5d6edd0-da90-4e24-9f2f-fdddee9866d8", {}, [])

        # Verify error details
        assert exc_info.value.code == "object_not_found"
        assert "database" in str(exc_info.value).lower()

    @patch("obsidian_to_notion.notion.client.Client")
    def test_database_permission_error(self, mock_client_class):
        """Test handling of database permission error."""
        client = NotionMigrationClient("test-token")

        # Mock permission error
        response_mock = Mock()
        response_mock.status_code = 403
        error = APIResponseError(
            response_mock,
            "Insufficient permissions for this database",
            "restricted_resource",
        )
        client.client.pages.create = Mock(side_effect=error)

        # Attempt to create a page should raise the error
        with pytest.raises(APIResponseError) as exc_info:
            client.create_page("db-id", {}, [])

        # Verify error details
        assert exc_info.value.code == "restricted_resource"
        assert response_mock.status_code == 403

    @patch("obsidian_to_notion.notion.client.Client")
    def test_create_page_with_database_error_message(self, mock_client_class):
        """Test that database errors provide helpful context."""
        client = NotionMigrationClient("test-token")

        # Mock the specific error from the issue
        response_mock = Mock()
        response_mock.status_code = 400
        error_msg = (
            "Could not find database with ID: f5d6edd0-da90-4e24-9f2f-fdddee9866d8. "
            "Make sure the relevant pages and databases are shared with "
            "the integration."
        )
        error = APIResponseError(response_mock, error_msg, "validation_error")
        client.client.pages.create = Mock(side_effect=error)

        with pytest.raises(APIResponseError) as exc_info:
            client.create_page("f5d6edd0-da90-4e24-9f2f-fdddee9866d8", {}, [])

        # The error message should contain helpful information
        error_str = str(exc_info.value)
        assert "database" in error_str.lower()
        assert "shared with the integration" in error_str
