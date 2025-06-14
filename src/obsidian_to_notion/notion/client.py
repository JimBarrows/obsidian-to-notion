"""Notion API client with rate limiting and error handling."""

import logging
import time
from typing import Any, Callable, Dict, List, Optional

from notion_client import APIResponseError, Client

from ..utils.error_handling import (
    NotionAPIError,
    create_error_context,
    log_error_with_context,
)

logger = logging.getLogger(__name__)


class NotionMigrationClient:
    """Notion API client with automatic rate limiting and retry logic."""

    def __init__(self, token: str, rate_limit_rps: int = 3):
        """Initialize the Notion client.

        Args:
            token: Notion API integration token
            rate_limit_rps: Maximum requests per second (default: 3)
        """
        self.client = Client(auth=token)
        self.request_timestamps: List[float] = []
        self.rate_limit_rps = rate_limit_rps

    def _enhance_error_message(self, error: APIResponseError) -> str:
        """Enhance API error messages with helpful context.

        Args:
            error: The API error

        Returns:
            Enhanced error message
        """
        base_message = str(error)

        # Database not found errors
        if error.code == "object_not_found" and "database" in base_message.lower():
            return (
                f"{base_message}\n\n"
                "To fix this error:\n"
                "1. Verify the database ID is correct\n"
                "2. Ensure the database is shared with your integration:\n"
                "   - Open the database in Notion\n"
                "   - Click 'Share' in the top right\n"
                "   - Invite your integration by name\n"
                "3. Check that your integration has the correct permissions"
            )

        # Permission errors
        elif error.code in ["restricted_resource", "unauthorized"]:
            return (
                f"{base_message}\n\n"
                "To fix this permission error:\n"
                "1. Ensure the database/page is shared with your integration\n"
                "2. Check that your integration token is valid\n"
                "3. Verify the integration has the necessary capabilities"
            )

        # Validation errors mentioning database
        elif error.code == "validation_error" and "database" in base_message.lower():
            return (
                f"{base_message}\n\n"
                "This typically means:\n"
                "1. The database ID may be incorrect\n"
                "2. The database needs to be shared with your integration\n"
                "3. The database may have been deleted or archived"
            )

        return base_message

    def rate_limited_request(
        self, method: Callable[..., Any], **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        """Execute API request with automatic rate limiting.

        Args:
            method: The API method to call
            **kwargs: Arguments to pass to the method

        Returns:
            The API response or None if all retries failed
        """
        # Ensure we don't exceed rate limit
        current_time = time.time()
        self.request_timestamps = [
            t for t in self.request_timestamps if current_time - t < 1.0
        ]

        if len(self.request_timestamps) >= self.rate_limit_rps:
            sleep_time = 1.0 - (current_time - self.request_timestamps[0])
            if sleep_time > 0:
                time.sleep(sleep_time)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = method(**kwargs)
                self.request_timestamps.append(time.time())
                return result  # type: ignore[no-any-return]
            except APIResponseError as e:
                # Extract method details for context
                method_name = (
                    method.__name__ if hasattr(method, "__name__") else str(method)
                )

                # Create base context
                context = create_error_context(
                    phase="notion_api_call",
                    api_method=method_name,
                    api_error_code=e.code,
                    api_status=e.status if hasattr(e, "status") else None,
                    retry_attempt=attempt + 1,
                    max_retries=max_retries,
                    kwargs=kwargs,
                )

                if e.code == "rate_limited":
                    retry_after = int(e.headers.get("retry-after", 1))
                    context["retry_after_seconds"] = retry_after
                    logger.warning(
                        f"Rate limited, waiting {retry_after} seconds...", extra=context
                    )
                    time.sleep(retry_after)
                elif attempt == max_retries - 1:
                    enhanced_message = self._enhance_error_message(e)
                    context["enhanced_message"] = enhanced_message
                    context["original_error"] = str(e)

                    # Convert to our NotionAPIError and log with full context
                    notion_error = NotionAPIError(enhanced_message)
                    notion_error.__cause__ = e
                    log_error_with_context(logger, notion_error, context)
                    raise notion_error from e
                else:
                    wait_time = 2**attempt
                    context["wait_time_seconds"] = wait_time
                    logger.warning(
                        f"API error on attempt {attempt + 1}, "
                        f"retrying in {wait_time}s: {e}",
                        extra=context,
                    )
                    time.sleep(wait_time)

        return None

    def create_page(
        self, database_id: str, properties: Dict, children: Optional[List] = None
    ) -> Optional[Dict]:
        """Create a new page in Notion database.

        Args:
            database_id: ID of the database to create the page in
            properties: Page properties
            children: Optional list of blocks to add as children

        Returns:
            The created page object or None if failed
        """
        try:
            # Extract title for logging context
            title = None
            for _, prop_value in properties.items():
                if isinstance(prop_value, dict) and prop_value.get("type") == "title":
                    title_content = prop_value.get("title", [])
                    if title_content and isinstance(title_content[0], dict):
                        title = title_content[0].get("text", {}).get("content", "")
                        break

            return self.rate_limited_request(
                self.client.pages.create,
                parent={"database_id": database_id},
                properties=properties,
                children=children or [],
                # Additional context for logging
                page_title=title,
                database_id=database_id,
            )
        except Exception as e:
            # Add page creation specific context
            context = create_error_context(
                phase="page_creation",
                database_id=database_id,
                page_title=title if "title" in locals() else None,
                has_children=bool(children),
                num_children=len(children) if children else 0,
            )
            log_error_with_context(logger, e, context)
            raise

    def update_page(
        self,
        page_id: str,
        properties: Optional[Dict] = None,
        children: Optional[List] = None,
    ) -> Optional[Dict]:
        """Update an existing page.

        Args:
            page_id: ID of the page to update
            properties: Optional properties to update
            children: Optional list of blocks to append

        Returns:
            The updated page object or None if failed
        """
        result = None

        if properties:
            result = self.rate_limited_request(
                self.client.pages.update, page_id=page_id, properties=properties
            )

        if children:
            # Append new blocks to the page
            self.rate_limited_request(
                self.client.blocks.children.append, block_id=page_id, children=children
            )
            if not result:
                result = {"id": page_id}

        return result or {"id": page_id}

    def query_database(
        self, database_id: str, filter_query: Optional[Dict] = None
    ) -> List[Dict]:
        """Query database for existing pages.

        Args:
            database_id: ID of the database to query
            filter_query: Optional filter to apply

        Returns:
            List of pages matching the query
        """
        all_results = []
        has_more = True
        start_cursor = None

        while has_more:
            query_params: Dict[str, Any] = {"database_id": database_id}
            if filter_query:
                query_params["filter"] = filter_query
            if start_cursor:
                query_params["start_cursor"] = start_cursor

            response = self.rate_limited_request(
                self.client.databases.query, **query_params
            )

            if response:
                all_results.extend(response.get("results", []))
                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")
            else:
                break

        return all_results

    def upload_file(self, file_path: str) -> Optional[str]:
        """Upload file to Notion and return file URL.

        Args:
            file_path: Path to the file to upload

        Returns:
            The file URL or None if upload failed
        """
        # Note: The Notion API doesn't have a direct file upload endpoint
        # Files must be uploaded to external storage (S3, Cloudinary, etc.)
        # and then referenced by URL in Notion blocks
        from pathlib import Path

        file_path_obj = Path(file_path)
        context = create_error_context(
            phase="file_upload",
            file_path=file_path,
            file_name=file_path_obj.name,
            file_exists=file_path_obj.exists(),
            file_size=file_path_obj.stat().st_size if file_path_obj.exists() else None,
            warning_type="NotImplemented",
        )

        logger.warning(
            f"File upload not implemented. File {file_path} needs to be "
            "uploaded to external storage and referenced by URL.",
            extra=context,
        )
        return None


class DeduplicationManager:
    """Manages deduplication of pages to prevent creating duplicates."""

    def __init__(self, notion_client: NotionMigrationClient, database_id: str):
        """Initialize the deduplication manager.

        Args:
            notion_client: The Notion client instance
            database_id: ID of the database to check for duplicates
        """
        self.notion = notion_client
        self.database_id = database_id
        self.existing_pages: Dict[str, str] = {}

    def load_existing_pages(self) -> None:
        """Build index of existing pages in Notion database."""
        logger.info("Loading existing pages for deduplication...")
        results = self.notion.query_database(self.database_id)

        for page in results:
            title = self.extract_title(page)
            if title:
                self.existing_pages[title.lower()] = page["id"]

        logger.info(f"Found {len(self.existing_pages)} existing pages")

    def should_skip_page(self, title: str) -> bool:
        """Check if page already exists.

        Args:
            title: Title of the page to check

        Returns:
            True if page should be skipped (already exists)
        """
        return title.lower() in self.existing_pages

    def get_existing_page_id(self, title: str) -> Optional[str]:
        """Get ID of existing page if it exists.

        Args:
            title: Title of the page to look up

        Returns:
            Page ID if exists, None otherwise
        """
        return self.existing_pages.get(title.lower())

    def extract_title(self, page: Dict) -> Optional[str]:
        """Extract title from Notion page object.

        Args:
            page: Notion page object

        Returns:
            The page title or None if not found
        """
        # Try different possible title property names
        for prop_name in ["Name", "Title", "title", "name"]:
            title_prop = page.get("properties", {}).get(prop_name, {})
            if title_prop.get("type") == "title":
                texts = title_prop.get("title", [])
                if texts:
                    text_content = texts[0].get("text", {}).get("content", "")
                    return text_content  # type: ignore[no-any-return]
        return None
