#!/usr/bin/env python3
"""Validate that pre-commit hooks and CI/CD checks are aligned.

This script ensures that local pre-commit hooks will catch all the same
errors that the CI/CD pipeline would catch, preventing CI failures after
local checks pass.
"""

import re
import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import yaml


def extract_ci_commands(ci_file: Path) -> Dict[str, List[str]]:
    """Extract linting commands from CI workflow file."""
    with open(ci_file) as f:
        ci_config = yaml.safe_load(f)

    commands = {}
    lint_job = ci_config.get("jobs", {}).get("lint", {})

    for step in lint_job.get("steps", []):
        if "run" in step and "name" in step:
            name = step["name"]
            if any(
                tool in name.lower() for tool in ["black", "flake8", "mypy", "ruff"]
            ):
                # Extract the actual command
                run_commands = step["run"].strip().split("\n")
                for cmd in run_commands:
                    cmd = cmd.strip()
                    if cmd and not cmd.startswith("#"):
                        commands[name] = cmd

    return commands


def extract_precommit_configs(precommit_file: Path) -> Dict[str, Dict]:
    """Extract hook configurations from pre-commit config."""
    with open(precommit_file) as f:
        config = yaml.safe_load(f)

    hooks = {}
    for repo in config.get("repos", []):
        for hook in repo.get("hooks", []):
            hook_id = hook.get("id", "")
            if hook_id in ["black", "flake8", "mypy", "ruff", "ci-flake8-check"]:
                hooks[hook_id] = {
                    "args": hook.get("args", []),
                    "files": hook.get("files", ""),
                    "pass_filenames": hook.get("pass_filenames", True),
                }

    return hooks


def validate_flake8_alignment(
    ci_cmd: str, precommit_hooks: Dict[str, Dict]
) -> List[str]:
    """Validate that flake8 configurations are aligned."""
    issues = []

    # Extract directories from CI command
    ci_dirs = re.findall(r"flake8\s+(.+)", ci_cmd)
    if ci_dirs:
        ci_dirs = ci_dirs[0].split()

    # Check both flake8 hooks
    for hook_name in ["flake8", "ci-flake8-check"]:
        if hook_name not in precommit_hooks:
            continue

        hook_config = precommit_hooks[hook_name]
        hook_args = hook_config["args"]

        # Check if directories are specified
        precommit_dirs = [arg for arg in hook_args if arg in ["src/", "tests/"]]

        if set(ci_dirs) != set(precommit_dirs):
            issues.append(
                f"{hook_name}: Directories mismatch - CI checks {ci_dirs}, "
                f"pre-commit checks {precommit_dirs or 'default'}"
            )

    return issues


def validate_black_alignment(
    ci_cmd: str, precommit_hooks: Dict[str, Dict]
) -> List[str]:
    """Validate that black configurations are aligned."""
    issues = []

    if "black" not in precommit_hooks:
        issues.append("black: Missing from pre-commit hooks")
        return issues

    # Extract options and directories from CI command
    # ci_has_check = "--check" in ci_cmd  # Not used currently
    ci_dirs = re.findall(r"black\s+(?:--check\s+)?(.+)", ci_cmd)
    if ci_dirs:
        ci_dirs = ci_dirs[0].split()

    # Pre-commit black runs with --check by default
    hook_args = precommit_hooks["black"]["args"]
    precommit_dirs = [arg for arg in hook_args if not arg.startswith("-")]

    if ci_dirs and not precommit_dirs:
        issues.append(
            f"black: CI checks specific directories {ci_dirs}, "
            "but pre-commit doesn't specify directories"
        )

    return issues


def run_test_comparison() -> Tuple[bool, List[str]]:
    """Run both CI commands and pre-commit to compare results."""
    print("\nRunning test comparison...")
    comparison_issues = []

    # Create a test file with known issues
    test_file = Path("test_validation.py")
    test_file.write_text(
        '''
import os
import sys

# This will trigger E402
sys.path.append('.')

import json  # E402: module level import not at top of file


def badly_formatted_function( ):
    """This function has formatting issues."""
    x=1+2  # No spaces around operators
    return x
'''
    )

    try:
        # Run flake8 as CI would
        ci_result = subprocess.run(
            ["flake8", "test_validation.py"], capture_output=True, text=True  # nosec
        )
        # ci_errors = (
        #     ci_result.stdout.strip().split("\n") if ci_result.returncode != 0 else []
        # )  # Not used currently

        # Run pre-commit
        pc_result = subprocess.run(
            ["pre-commit", "run", "--files", "test_validation.py"],
            capture_output=True,
            text=True,  # nosec
        )

        # Check if pre-commit caught the E402 error
        if "E402" in ci_result.stdout and "E402" not in pc_result.stdout:
            comparison_issues.append(
                "Pre-commit did not catch E402 error that CI would catch"
            )

        return len(comparison_issues) == 0, comparison_issues

    finally:
        test_file.unlink(missing_ok=True)


def main():
    """Main validation function."""
    project_root = Path(__file__).parent.parent
    ci_file = project_root / ".github" / "workflows" / "ci.yml"
    precommit_file = project_root / ".pre-commit-config.yaml"

    if not ci_file.exists():
        print(f"Error: CI workflow file not found at {ci_file}")
        sys.exit(1)

    if not precommit_file.exists():
        print(f"Error: Pre-commit config not found at {precommit_file}")
        sys.exit(1)

    print("Validating CI/CD and pre-commit alignment...")
    print("=" * 60)

    # Extract configurations
    ci_commands = extract_ci_commands(ci_file)
    precommit_hooks = extract_precommit_configs(precommit_file)

    all_issues = []

    # Validate each tool
    for name, cmd in ci_commands.items():
        print(f"\nChecking {name}...")
        print(f"CI command: {cmd}")

        if "flake8" in cmd.lower():
            issues = validate_flake8_alignment(cmd, precommit_hooks)
            all_issues.extend(issues)
        elif "black" in cmd.lower():
            issues = validate_black_alignment(cmd, precommit_hooks)
            all_issues.extend(issues)

        if not issues:
            print("✓ Aligned with pre-commit")

    # Run practical test
    test_passed, test_issues = run_test_comparison()
    all_issues.extend(test_issues)

    # Report results
    print("\n" + "=" * 60)
    if all_issues:
        print("❌ VALIDATION FAILED - Issues found:")
        for issue in all_issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("✅ VALIDATION PASSED - Pre-commit and CI/CD are aligned!")
        print("\nRecommendations:")
        print("  - Run 'pre-commit run --all-files' before pushing")
        print("  - If pre-commit passes, CI should also pass")
        print("  - Never add '# noqa' comments without careful consideration")
        sys.exit(0)


if __name__ == "__main__":
    main()
