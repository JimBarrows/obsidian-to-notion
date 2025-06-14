"""Step definitions for metadata mapping feature tests."""

from behave import given, then
from behave.runner import Context


@given("the Notion database has the following properties")
def step_notion_database_properties(context: Context) -> None:
    """Set up expected Notion database properties."""
    context.notion_properties = {}
    for row in context.table:
        context.notion_properties[row["property_name"]] = row["property_type"]


# Note: The @given('I have a markdown file "{filepath}" with content') step is defined
# in text_splitting_steps.py to handle both regular content and long text placeholders


@then('the Notion page should have property "{property_name}" with values')
def step_verify_notion_multi_select_property(
    context: Context, property_name: str
) -> None:
    """Verify a multi-select property has the expected values."""
    # Get the created page from context
    page = context.created_pages[-1]

    # Check the property exists
    assert (
        property_name in page["properties"]
    ), f"Property '{property_name}' not found in page"

    # Get the property value
    prop = page["properties"][property_name]
    assert (
        prop["type"] == "multi_select"
    ), f"Property '{property_name}' is not multi_select type"

    # Extract the values
    actual_values = {item["name"] for item in prop["multi_select"]}
    expected_values = {row["value"] for row in context.table}

    assert (
        actual_values == expected_values
    ), f"Expected values {expected_values}, but got {actual_values}"


@then('the Notion page should have property "{property_name}" with value "{value}"')
def step_verify_notion_text_property(
    context: Context, property_name: str, value: str
) -> None:
    """Verify a text property has the expected value."""
    # Get the created page from context
    page = context.created_pages[-1]

    # Check the property exists
    assert (
        property_name in page["properties"]
    ), f"Property '{property_name}' not found in page"

    # Get the property value based on type
    prop = page["properties"][property_name]

    if prop["type"] == "rich_text":
        actual_value = (
            prop["rich_text"][0]["text"]["content"] if prop["rich_text"] else ""
        )
    elif prop["type"] == "url":
        actual_value = prop["url"] or ""
    else:
        raise AssertionError(f"Unexpected property type: {prop['type']}")

    assert actual_value == value, f"Expected '{value}', but got '{actual_value}'"


@then('the Notion page should have property "{property_name}" with date "{date}"')
def step_verify_notion_date_property(
    context: Context, property_name: str, date: str
) -> None:
    """Verify a date property has the expected value."""
    # Get the created page from context
    page = context.created_pages[-1]

    # Check the property exists
    assert (
        property_name in page["properties"]
    ), f"Property '{property_name}' not found in page"

    # Get the property value
    prop = page["properties"][property_name]
    assert prop["type"] == "date", f"Property '{property_name}' is not date type"

    actual_date = prop["date"]["start"] if prop["date"] else None

    assert actual_date == date, f"Expected date '{date}', but got '{actual_date}'"
