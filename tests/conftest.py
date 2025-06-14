from unittest.mock import MagicMock

import pytest

from obsidian_to_notion.notion import NotionMigrationClient


@pytest.fixture
def mock_notion_client():
    """Mock Notion client for testing."""
    client = MagicMock(spec=NotionMigrationClient)
    client.create_page.return_value = {"id": "test-page-id"}
    client.query_database.return_value = []
    return client
