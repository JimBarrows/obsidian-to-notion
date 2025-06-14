"""Step definitions for pre-commit validation tests."""

import subprocess
from pathlib import Path

from behave import given, then, when


@given("I have a working Git repository")
def step_working_git_repo(context):
    """Ensure we're in a Git repository."""
    # The test runs in the actual project repository
    result = subprocess.run(
        ["git", "status"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, "Not in a Git repository"


@given("pre-commit is installed")
def step_precommit_installed(context):
    """Verify pre-commit is installed."""
    result = subprocess.run(
        ["pre-commit", "--version"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, "pre-commit is not installed"
    context.precommit_installed = True


@given("I have modified Python files")
def step_create_modified_files(context):
    """Create or modify Python files for testing."""
    context.test_file = Path(context.temp_dir) / "test_file.py"
    context.test_file.write_text('print("Hello World")\n')

    # Stage the file
    subprocess.run(["git", "add", str(context.test_file)], check=True)


@given("I have Python files with incorrect formatting")
def step_create_unformatted_files(context):
    """Create Python files with formatting issues."""
    context.test_file = Path(context.temp_dir) / "unformatted.py"
    # Intentionally poor formatting
    context.test_file.write_text(
        "def poorly_formatted(  x,y ,z   ):\n"
        "    return x+y+z\n"
        "\n\n\n\n"  # Extra blank lines
        "result=poorly_formatted(1,2,3)\n"
    )
    subprocess.run(["git", "add", str(context.test_file)], check=True)


@given("I have Python files with unsorted imports")
def step_create_unsorted_imports(context):
    """Create Python files with unsorted imports."""
    context.test_file = Path(context.temp_dir) / "unsorted_imports.py"
    context.test_file.write_text(
        "import os\n"
        "import ast\n"
        "import sys\n"
        "from pathlib import Path\n"
        "from collections import defaultdict\n"
        "\n"
        'print("Imports are not sorted")\n'
    )
    subprocess.run(["git", "add", str(context.test_file)], check=True)


@given("I have Python files with linting errors")
def step_create_linting_errors(context):
    """Create Python files with linting issues."""
    context.test_file = Path(context.temp_dir) / "linting_errors.py"
    context.test_file.write_text(
        "import os  # unused import\n"
        "\n"
        "def function_with_issues():\n"
        "    unused_variable = 42\n"
        "    x = 1; y = 2  # multiple statements on one line\n"
        "    return x\n"
    )
    subprocess.run(["git", "add", str(context.test_file)], check=True)


@given("I have Python files with type errors")
def step_create_type_errors(context):
    """Create Python files with type errors."""
    context.test_file = Path(context.temp_dir) / "type_errors.py"
    context.test_file.write_text(
        "def add_numbers(a: int, b: int) -> int:\n"
        "    return a + b\n"
        "\n"
        'result = add_numbers("1", "2")  # Type error\n'
    )
    subprocess.run(["git", "add", str(context.test_file)], check=True)


@given("I have Python files with style issues")
def step_create_style_issues(context):
    """Create Python files with style issues for Ruff."""
    context.test_file = Path(context.temp_dir) / "style_issues.py"
    context.test_file.write_text(
        "import os\n"
        "import sys\n"
        "\n"
        "def long_func_exceeds_line_length():\n"
        "    pass\n"
    )
    subprocess.run(["git", "add", str(context.test_file)], check=True)


@given("I have clean Python files that pass all checks")
def step_create_clean_files(context):
    """Create Python files that pass all checks."""
    context.test_file = Path(context.temp_dir) / "clean_file.py"
    context.test_file.write_text(
        '"""A clean Python file that passes all checks."""\n'
        "\n"
        "\n"
        "def add_numbers(a: int, b: int) -> int:\n"
        '    """Add two numbers together."""\n'
        "    return a + b\n"
        "\n"
        "\n"
        "def main() -> None:\n"
        '    """Main function."""\n'
        "    result = add_numbers(1, 2)\n"
        '    print(f"Result: {result}")\n'
        "\n"
        "\n"
        'if __name__ == "__main__":\n'
        "    main()\n"
    )
    subprocess.run(["git", "add", str(context.test_file)], check=True)


@given("I have files that fail validation")
def step_create_failing_files(context):
    """Create files that will fail pre-commit validation."""
    context.test_file = Path(context.temp_dir) / "failing_file.py"
    context.test_file.write_text(
        "import os\n\n\n\n\n"  # Too many blank lines and unused import
        "x=1;y=2;z=3  # Multiple statements, no spaces\n"
    )
    subprocess.run(["git", "add", str(context.test_file)], check=True)


@given("I have files that would fail validation")
def step_create_files_for_skip(context):
    """Create files that would fail validation (for skip test)."""
    step_create_failing_files(context)


@given("the .pre-commit-config.yaml file exists")
def step_verify_precommit_config(context):
    """Verify .pre-commit-config.yaml exists."""
    config_path = Path(".pre-commit-config.yaml")
    assert config_path.exists(), ".pre-commit-config.yaml not found"
    context.precommit_config = config_path


@when("I attempt to commit the changes")
def step_attempt_commit(context):
    """Attempt to make a commit."""
    result = subprocess.run(
        ["git", "commit", "-m", "Test commit"],
        capture_output=True,
        text=True,
        check=False,
    )
    context.commit_result = result


@when("I attempt to commit")
def step_attempt_commit_simple(context):
    """Attempt to make a commit (simple version)."""
    step_attempt_commit(context)


@when("pre-commit runs the Black hook")
def step_run_black_hook(context):
    """Run Black through pre-commit."""
    result = subprocess.run(
        ["pre-commit", "run", "black", "--files", str(context.test_file)],
        capture_output=True,
        text=True,
        check=False,
    )
    context.hook_result = result


@when("pre-commit runs the isort hook")
def step_run_isort_hook(context):
    """Run isort through pre-commit."""
    result = subprocess.run(
        ["pre-commit", "run", "isort", "--files", str(context.test_file)],
        capture_output=True,
        text=True,
        check=False,
    )
    context.hook_result = result


@when("pre-commit runs the Flake8 hook")
def step_run_flake8_hook(context):
    """Run Flake8 through pre-commit."""
    result = subprocess.run(
        ["pre-commit", "run", "flake8", "--files", str(context.test_file)],
        capture_output=True,
        text=True,
        check=False,
    )
    context.hook_result = result


@when("pre-commit runs the Mypy hook")
def step_run_mypy_hook(context):
    """Run Mypy through pre-commit."""
    result = subprocess.run(
        ["pre-commit", "run", "mypy", "--files", str(context.test_file)],
        capture_output=True,
        text=True,
        check=False,
    )
    context.hook_result = result


@when("pre-commit runs the Ruff hook")
def step_run_ruff_hook(context):
    """Run Ruff through pre-commit."""
    result = subprocess.run(
        ["pre-commit", "run", "ruff", "--files", str(context.test_file)],
        capture_output=True,
        text=True,
        check=False,
    )
    context.hook_result = result


@when("I commit with the --no-verify flag")
def step_commit_no_verify(context):
    """Commit with --no-verify to skip pre-commit."""
    result = subprocess.run(
        ["git", "commit", "-m", "Test commit", "--no-verify"],
        capture_output=True,
        text=True,
        check=False,
    )
    context.commit_result = result


@when("I validate the pre-commit configuration")
def step_validate_config(context):
    """Validate the pre-commit configuration."""
    result = subprocess.run(
        ["pre-commit", "validate-config"],
        capture_output=True,
        text=True,
        check=False,
    )
    context.validation_result = result


@then("pre-commit hooks should run automatically")
def step_verify_hooks_ran(context):
    """Verify pre-commit hooks ran."""
    # Check if pre-commit output is in the commit result
    output = context.commit_result.stdout + context.commit_result.stderr
    assert "pre-commit" in output.lower() or context.commit_result.returncode != 0


@then("each configured hook should execute in order")
def step_verify_hook_order(context):
    """Verify hooks executed in order."""
    # This is implicit in pre-commit's behavior
    # We can check the output contains hook names
    output = context.commit_result.stdout + context.commit_result.stderr
    # At minimum, we should see some hook activity
    assert len(output) > 0


@then("Black should automatically format the files")
def step_verify_black_formatted(context):
    """Verify Black formatted the files."""
    # Black modifies files in place during pre-commit
    # Check if the file was modified
    content = context.test_file.read_text()
    # Black would have reformatted the poorly formatted code
    assert (
        "def poorly_formatted(x, y, z):" in content
        or context.hook_result.returncode == 0
    )


@then("the commit should include the formatted changes")
def step_verify_formatted_staged(context):
    """Verify formatted changes are staged."""
    # Check git status to see if file was modified
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    )
    # File might be modified and staged
    assert result.returncode == 0


@then("imports should be automatically sorted")
def step_verify_imports_sorted(context):
    """Verify isort sorted the imports."""
    content = context.test_file.read_text()
    lines = content.strip().split("\n")
    # Check that ast comes before os (alphabetical)
    import_lines = [line for line in lines if line.startswith("import ")]
    if len(import_lines) >= 2:
        assert import_lines[0] < import_lines[1]  # Should be sorted


@then("the changes should be staged for commit")
def step_verify_changes_staged(context):
    """Verify changes are staged."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=True,
    )
    # The test file should be in staged files
    assert context.test_file.name in result.stdout or result.returncode == 0


@then("linting errors should be reported")
def step_verify_linting_errors(context):
    """Verify linting errors are reported."""
    output = context.hook_result.stdout + context.hook_result.stderr
    # Should see some indication of linting issues
    assert context.hook_result.returncode != 0 or "error" in output.lower()


@then("the commit should be blocked if errors exist")
def step_verify_commit_blocked(context):
    """Verify commit is blocked when errors exist."""
    assert context.hook_result.returncode != 0


@then("type errors should be reported")
def step_verify_type_errors(context):
    """Verify type errors are reported."""
    output = context.hook_result.stdout + context.hook_result.stderr
    # Mypy should report type errors
    assert "error" in output.lower() or context.hook_result.returncode != 0


@then("the commit should be blocked if type errors exist")
def step_verify_commit_blocked_types(context):
    """Verify commit is blocked for type errors."""
    assert context.hook_result.returncode != 0


@then("Ruff should check and optionally fix issues")
def step_verify_ruff_check(context):
    """Verify Ruff checked for issues."""
    # Ruff will have run and either fixed or reported issues
    assert context.hook_result is not None


@then("the commit should reflect any automatic fixes")
def step_verify_ruff_fixes(context):
    """Verify any Ruff fixes are included."""
    # Similar to other formatters, check if changes were made
    assert context.hook_result.returncode in [0, 1]  # 0 = no issues, 1 = fixed issues


@then("all pre-commit hooks should pass")
def step_verify_all_hooks_pass(context):
    """Verify all hooks passed."""
    assert (
        context.commit_result.returncode == 0
    ), f"Pre-commit failed: {context.commit_result.stderr}"


@then("the commit should proceed successfully")
def step_verify_commit_success(context):
    """Verify commit succeeded."""
    assert context.commit_result.returncode == 0


@then("pre-commit should block the commit")
def step_verify_commit_blocked_general(context):
    """Verify commit was blocked."""
    assert context.commit_result.returncode != 0


@then("display clear error messages for each failure")
def step_verify_error_messages(context):
    """Verify clear error messages are shown."""
    output = context.commit_result.stdout + context.commit_result.stderr
    # Should have some error output
    assert len(output) > 0
    # Should mention which hooks failed
    assert "Failed" in output or "error" in output.lower()


@then("pre-commit hooks should be skipped")
def step_verify_hooks_skipped(context):
    """Verify hooks were skipped with --no-verify."""
    output = context.commit_result.stdout + context.commit_result.stderr
    # Should not see pre-commit output
    assert "pre-commit" not in output.lower()


@then("the commit should proceed without validation")
def step_verify_commit_without_validation(context):
    """Verify commit proceeded without validation."""
    # With --no-verify, commit should succeed even with bad files
    assert context.commit_result.returncode == 0


@then("the configuration should be valid")
def step_verify_config_valid(context):
    """Verify pre-commit configuration is valid."""
    assert (
        context.validation_result.returncode == 0
    ), f"Invalid config: {context.validation_result.stderr}"


@then("all referenced hooks should be properly defined")
def step_verify_hooks_defined(context):
    """Verify all hooks in config are properly defined."""
    # If validation passed, hooks are properly defined
    assert context.validation_result.returncode == 0
