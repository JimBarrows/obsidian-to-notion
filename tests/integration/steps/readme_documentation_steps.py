"""Step definitions for README documentation tests."""

import re
from pathlib import Path

from behave import given, then, when


@given("I have the README.md file")
def step_have_readme_file(context):
    """Ensure README.md exists and load its content."""
    # Look for README.md in project root
    readme_path = Path("../../README.md")
    if not readme_path.exists():
        # Try from project root if running from there
        readme_path = Path("README.md")
    assert readme_path.exists(), f"README.md file not found at {readme_path.absolute()}"
    context.readme_content = readme_path.read_text()
    context.readme_lines = context.readme_content.splitlines()


@when("I look for virtual environment setup instructions")
def step_look_for_venv_setup(context):
    """Find virtual environment setup command in README."""
    context.venv_commands = []
    for i, line in enumerate(context.readme_lines):
        if "venv" in line and "-m" in line:
            context.venv_commands.append((i + 1, line))


@when("I look for dry-run command examples")
def step_look_for_dry_run(context):
    """Find dry-run command examples in README."""
    context.dry_run_commands = []
    for i, line in enumerate(context.readme_lines):
        if "--dry-run" in line:
            context.dry_run_commands.append((i + 1, line))


@when("I look for migration execution examples")
def step_look_for_migration_execution(context):
    """Find migration execution command examples in README."""
    context.migration_commands = []
    for i, line in enumerate(context.readme_lines):
        if "migrate.py" in line and "--dry-run" not in line:
            context.migration_commands.append((i + 1, line))


@when("I search for all Python command examples")
def step_search_all_python_commands(context):
    """Find all Python command examples in README."""
    context.python_commands = []
    # Look for lines that contain python commands
    # Pattern matches 'python' followed by space or newline, but not 'python3'
    pattern = r"\bpython(?!3)\s"
    for i, line in enumerate(context.readme_lines):
        if re.search(pattern, line):
            context.python_commands.append((i + 1, line))


@then('the command should use "python3" not "python"')
def step_verify_python3_command(context):
    """Verify commands use python3."""
    commands_to_check = []

    if hasattr(context, "venv_commands"):
        commands_to_check.extend(context.venv_commands)
    elif hasattr(context, "dry_run_commands"):
        commands_to_check.extend(context.dry_run_commands)
    elif hasattr(context, "migration_commands"):
        commands_to_check.extend(context.migration_commands)

    for line_num, line in commands_to_check:
        assert "python3" in line, f"Line {line_num} should use 'python3': {line}"
        # Make sure it's not using plain 'python '
        assert not re.search(
            r"\bpython(?!3)\s", line
        ), f"Line {line_num} uses 'python' instead of 'python3': {line}"


@then('all commands should use "python3" not "python"')
def step_verify_all_python3(context):
    """Verify all Python commands use python3."""
    # Check that we don't have any plain 'python ' commands
    for line_num, line in context.python_commands:
        raise AssertionError(
            f"Line {line_num} uses 'python' instead of 'python3': {line}"
        )


@then('there should be no instances of "python " without the "3"')
def step_no_plain_python(context):
    """Verify no plain python commands exist."""
    # This checks the entire file for any 'python ' without '3'
    pattern = r"\bpython(?!3)\s"
    matches = []
    for i, line in enumerate(context.readme_lines):
        if re.search(pattern, line):
            matches.append((i + 1, line))

    assert (
        len(matches) == 0
    ), f"Found {len(matches)} instances of 'python' without '3': {matches}"
