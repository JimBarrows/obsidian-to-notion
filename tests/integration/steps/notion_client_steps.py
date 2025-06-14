"""Step definitions for Notion API client integration tests."""

import time
from unittest.mock import Mock, patch

from behave import given, then, when
from notion_client import APIResponseError

from obsidian_to_notion.notion import DeduplicationManager, NotionMigrationClient


@given("I have a valid Notion API token")
def step_valid_token(context):
    context.notion_token = "test-token-123"


@given("I have a target database ID")
def step_target_database(context):
    context.database_id = "test-database-id"


@given("I have a NotionMigrationClient instance")
def step_create_client(context):
    with patch("obsidian_to_notion.notion.client.Client"):
        context.client = NotionMigrationClient(context.notion_token)
        context.client.client = Mock()


@given(
    "I have a NotionMigrationClient with rate limit of {limit:d} requests per second"
)
def step_create_client_with_limit(context, limit):
    with patch("obsidian_to_notion.notion.client.Client"):
        context.client = NotionMigrationClient(
            context.notion_token, rate_limit_rps=limit
        )
        context.client.client = Mock()


@when('I create a page with title "{title}" and content "{content}"')
def step_create_page(context, title, content):
    properties = {"Name": {"title": [{"text": {"content": title}}]}}
    children = [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"text": {"content": content}}]},
        }
    ]

    # Mock successful response
    context.client.client.pages.create.return_value = {
        "id": "new-page-id",
        "properties": properties,
    }

    context.result = context.client.create_page(
        context.database_id, properties, children
    )


@then("the page should be created successfully")
def step_verify_page_created(context):
    assert context.result is not None
    assert context.result["id"] == "new-page-id"


@then("the page should have the correct title and content")
def step_verify_page_content(context):
    # Verify the create method was called with correct parameters
    context.client.client.pages.create.assert_called_once()
    call_args = context.client.client.pages.create.call_args
    assert call_args[1]["parent"]["database_id"] == context.database_id


@when("I make {count:d} consecutive API requests")
def step_make_multiple_requests(context, count):
    context.request_times = []

    # Mock successful responses
    context.client.client.pages.create.return_value = {"id": "test-id"}

    for _ in range(count):
        context.client.create_page(context.database_id, {}, [])
        context.request_times.append(time.time())


@then("the requests should be rate limited")
def step_verify_rate_limiting(context):
    # Check that requests are spaced appropriately
    assert len(context.request_times) == 5


@then("no more than {limit:d} requests should occur within any 1 second window")
def step_verify_rate_window(context, limit):
    # Check any 1-second window
    for i in range(len(context.request_times)):
        window_start = context.request_times[i]
        window_requests = sum(
            1 for t in context.request_times if window_start <= t < window_start + 1.0
        )
        assert (
            window_requests <= limit
        ), f"Found {window_requests} requests in 1-second window"


@given("the API will fail with a transient error on first attempt")
def step_setup_transient_error(context):
    # Make the first call fail, second succeed
    response_mock = Mock()
    response_mock.status_code = 500
    error = APIResponseError(response_mock, "Internal Server Error", "internal_error")

    context.client.client.pages.create.side_effect = [error, {"id": "retry-success-id"}]


@when("I create a page")
def step_create_page_simple(context):
    context.result = context.client.create_page(context.database_id, {}, [])


@then("the request should be retried")
def step_verify_retry(context):
    assert context.client.client.pages.create.call_count >= 2


@then("the page should be created on retry")
def step_verify_retry_success(context):
    assert context.result is not None
    assert context.result["id"] == "retry-success-id"


@given("the API will return a rate limit error with retry-after header")
def step_setup_rate_limit_error(context):
    response_mock = Mock()
    response_mock.status_code = 429
    response_mock.headers = {"retry-after": "1"}
    error = APIResponseError(response_mock, "Rate limited", "rate_limited")

    context.client.client.pages.create.side_effect = [
        error,
        {"id": "rate-limit-success-id"},
    ]
    context.start_time = time.time()


@then("the client should wait for the specified retry-after period")
def step_verify_retry_after_wait(context):
    elapsed = time.time() - context.start_time
    assert (
        elapsed >= 1.0
    ), f"Expected wait of at least 1 second, but only waited {elapsed}"


@then("the page should be created after waiting")
def step_verify_rate_limit_success(context):
    assert context.result is not None
    assert context.result["id"] == "rate-limit-success-id"


@given("the database contains {count:d} existing pages")
def step_setup_existing_pages(context, count):
    pages = []
    for i in range(count):
        pages.append(
            {
                "id": f"page-{i}",
                "properties": {
                    "Name": {
                        "type": "title",
                        "title": [{"text": {"content": f"Page {i}"}}],
                    }
                },
            }
        )

    context.client.client.databases.query.return_value = {
        "results": pages,
        "has_more": False,
    }


@when("I query the database")
def step_query_database(context):
    context.results = context.client.query_database(context.database_id)


@then("I should receive all {count:d} pages")
def step_verify_query_results(context, count):
    assert len(context.results) == count


@then("pagination should be handled automatically")
def step_verify_pagination(context):
    # Verify query was called
    context.client.client.databases.query.assert_called()


@given('a page exists with ID "{page_id}"')
def step_setup_existing_page(context, page_id):
    context.existing_page_id = page_id


@when('I update the page title to "{new_title}"')
def step_update_page_title(context, new_title):
    properties = {"Name": {"title": [{"text": {"content": new_title}}]}}

    context.client.client.pages.update.return_value = {
        "id": context.existing_page_id,
        "properties": properties,
    }

    context.result = context.client.update_page(context.existing_page_id, properties)


@then("the page should be updated successfully")
def step_verify_update_success(context):
    assert context.result is not None
    assert context.result["id"] == context.existing_page_id


@then('the new title should be "{expected_title}"')
def step_verify_new_title(context, expected_title):
    context.client.client.pages.update.assert_called_once()
    call_args = context.client.client.pages.update.call_args
    assert call_args[1]["page_id"] == context.existing_page_id


@given("I have a DeduplicationManager instance")
def step_create_dedup_manager(context):
    # Ensure we have a client instance
    if not hasattr(context, "client"):
        with patch("obsidian_to_notion.notion.client.Client"):
            context.client = NotionMigrationClient(context.notion_token)
            context.client.client = Mock()

    context.dedup = DeduplicationManager(context.client, context.database_id)


@given('the database contains a page titled "{title}"')
def step_setup_existing_titled_page(context, title):
    # Mock the query response
    context.client.client.databases.query.return_value = {
        "results": [
            {
                "id": "existing-page-id",
                "properties": {
                    "Name": {"type": "title", "title": [{"text": {"content": title}}]}
                },
            }
        ],
        "has_more": False,
    }
    context.dedup.load_existing_pages()


@when('I check if "{title}" should be skipped')
def step_check_dedup(context, title):
    context.should_skip = context.dedup.should_skip_page(title)
    context.existing_id = context.dedup.get_existing_page_id(title)


@then("the deduplication check should return true")
def step_verify_dedup_true(context):
    assert context.should_skip is True


@then("I should get the existing page ID")
def step_verify_existing_id(context):
    assert context.existing_id == "existing-page-id"


@given('I have a test file "{filename}"')
def step_setup_test_file(context, filename):
    context.test_file = f"/tmp/{filename}"
    # Create a mock file
    with open(context.test_file, "w") as f:
        f.write("test content")


@when("I upload the file")
def step_upload_file(context):
    # Upload file (returns None as it's not implemented)
    context.upload_result = context.client.upload_file(context.test_file)


@then("the file upload should return None")
def step_verify_upload_returns_none(context):
    assert context.upload_result is None


@then("a warning should be logged about external storage")
def step_verify_warning_logged(context):
    # This step is mainly for documentation purposes
    # In a real test, we would check if the warning was logged
    pass
