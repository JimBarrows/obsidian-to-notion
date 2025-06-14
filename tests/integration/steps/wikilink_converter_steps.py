"""Step definitions for WikilinkConverter integration tests."""

import json

from behave import given, then, when

from obsidian_to_notion.transformers.wikilink_converter import WikilinkConverter


@given("I have a WikilinkConverter instance")
def step_create_wikilink_converter(context):
    """Create a WikilinkConverter instance."""
    context.converter = WikilinkConverter()


@given("I have a WikilinkConverter instance with cached pages")
def step_create_converter_with_cache(context):
    """Create a WikilinkConverter instance with some cached pages."""
    context.converter = WikilinkConverter()
    context.converter.add_page_to_cache("Valid Page", "page-123")
    context.converter.add_page_to_cache("Another", "page-456")


@when("I add pages to the cache")
def step_add_pages_to_cache(context):
    """Add pages to the converter cache."""
    for row in context.table:
        context.converter.add_page_to_cache(row["title"], row["page_id"])


@when("I convert content with wikilinks")
def step_convert_content_with_wikilinks(context):
    """Convert content with wikilinks."""
    context.results = []

    for row in context.table:
        content = row["content"]
        wikilinks_json = row["wikilinks"]

        # Parse the JSON string to get wikilinks list
        wikilinks = json.loads(wikilinks_json)

        result = context.converter.convert_content(content, wikilinks)
        context.results.append(
            {"original": content, "converted": result, "wikilinks": wikilinks}
        )


@when("I convert content with broken wikilinks")
def step_convert_content_with_broken_wikilinks(context):
    """Convert content with broken wikilinks."""
    context.results = []

    for row in context.table:
        content = row["content"]
        wikilinks_json = row["wikilinks"]

        wikilinks = json.loads(wikilinks_json)
        result = context.converter.convert_content(content, wikilinks)

        context.results.append(
            {"original": content, "converted": result, "wikilinks": wikilinks}
        )


@when('I parse content "{content}"')
def step_parse_content(context, content):
    """Parse content to get rich text objects."""
    context.parsed_result = context.converter.parse_notion_link_from_content(content)


@when('I create a mention for page "{page_id}" with text "{text}"')
def step_create_mention(context, page_id, text):
    """Create a Notion mention rich text object."""
    context.mention_result = context.converter.create_mention_rich_text(page_id, text)


@then("the content should contain Notion links")
def step_verify_notion_links(context):
    """Verify content contains Notion-formatted links."""
    for result in context.results:
        converted = result["converted"]
        # Should contain the @page-id format
        assert "@page-" in converted, f"No Notion links found in: {converted}"


@then('the content should contain "{expected_text}"')
def step_verify_content_contains(context, expected_text):
    """Verify content contains specific text."""
    for result in context.results:
        converted = result["converted"]
        assert (
            expected_text in converted
        ), f"Expected '{expected_text}' not found in: {converted}"


@then("no broken links should be reported")
def step_verify_no_broken_links(context):
    """Verify no broken links were reported."""
    report = context.converter.get_broken_links_report()
    assert "No broken links found" in report, f"Unexpected broken links: {report}"


@then("broken links should be reported")
def step_verify_broken_links_reported(context):
    """Verify broken links were reported."""
    report = context.converter.get_broken_links_report()
    assert (
        "No broken links found" not in report
    ), "Expected broken links but none were reported"
    assert len(context.converter.broken_links) > 0, "No broken links in the list"


@then("the broken links report should list all missing pages")
def step_verify_broken_links_report(context):
    """Verify broken links report contains all missing pages."""
    report = context.converter.get_broken_links_report()

    # Extract expected missing pages from the test data
    expected_missing = set()
    for result in context.results:
        for link in result["wikilinks"]:
            expected_missing.add(link["note_name"])

    # Verify all missing pages are in the report
    for missing_page in expected_missing:
        assert (
            missing_page in report
        ), f"Missing page '{missing_page}' not in report: {report}"


@then("I should get rich text objects with mentions and text")
def step_verify_rich_text_objects(context):
    """Verify parsed result contains rich text objects."""
    result = context.parsed_result

    assert isinstance(result, list), "Result should be a list"
    assert len(result) > 0, "Result should not be empty"

    # Should have both text and mention objects
    has_text = any(obj.get("type") == "text" for obj in result)
    has_mention = any(obj.get("type") == "mention" for obj in result)

    assert has_text, "Should contain text objects"
    assert has_mention, "Should contain mention objects"


@then("I should get a valid Notion mention object")
def step_verify_mention_object(context):
    """Verify mention object structure."""
    mention = context.mention_result

    assert mention["type"] == "mention", "Should be a mention type"
    assert "mention" in mention, "Should have mention property"
    assert mention["mention"]["type"] == "page", "Should be a page mention"
    assert "page" in mention["mention"], "Should have page property"
    assert "id" in mention["mention"]["page"], "Should have page ID"
    assert "annotations" in mention, "Should have annotations"
    assert "plain_text" in mention, "Should have plain_text"
    assert "href" in mention, "Should have href"
