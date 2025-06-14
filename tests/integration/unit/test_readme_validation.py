"""Unit tests for README validation."""

import re
import unittest
from pathlib import Path


class TestReadmeValidation(unittest.TestCase):
    """Test cases for validating README.md content."""

    def setUp(self):
        """Set up test fixtures."""
        self.readme_path = Path("README.md")
        if self.readme_path.exists():
            self.readme_content = self.readme_path.read_text()
            self.readme_lines = self.readme_content.splitlines()
        else:
            self.readme_content = ""
            self.readme_lines = []

    def test_readme_exists(self):
        """Test that README.md exists in project root."""
        self.assertTrue(
            self.readme_path.exists(), "README.md not found in project root"
        )

    def test_no_bare_python_commands(self):
        """Test that README doesn't contain bare 'python' commands."""
        # Pattern to match 'python' followed by space, but not 'python3'
        pattern = r"\bpython(?!3)\s"

        bare_python_lines = []
        for i, line in enumerate(self.readme_lines):
            if re.search(pattern, line):
                bare_python_lines.append((i + 1, line))

        self.assertEqual(
            len(bare_python_lines),
            0,
            f"Found bare 'python' commands on lines: {bare_python_lines}",
        )

    def test_python3_used_in_venv_setup(self):
        """Test that virtual environment setup uses python3."""
        venv_lines = [
            (i + 1, line)
            for i, line in enumerate(self.readme_lines)
            if "venv" in line and "-m" in line
        ]

        for line_num, line in venv_lines:
            self.assertIn(
                "python3",
                line,
                f"Line {line_num} should use 'python3' for venv setup: {line}",
            )

    def test_python3_used_in_migrate_commands(self):
        """Test that migrate.py commands use python3."""
        migrate_lines = [
            (i + 1, line)
            for i, line in enumerate(self.readme_lines)
            if "migrate.py" in line
        ]

        for line_num, line in migrate_lines:
            if "python" in line:  # Only check lines that have python commands
                self.assertIn(
                    "python3",
                    line,
                    f"Line {line_num} should use 'python3' for migrate.py: {line}",
                )

    def test_all_code_blocks_use_python3(self):
        """Test that all code blocks with Python commands use python3."""
        in_code_block = False
        code_block_lines = []

        for i, line in enumerate(self.readme_lines):
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
            elif in_code_block and "python " in line:
                code_block_lines.append((i + 1, line))

        for line_num, line in code_block_lines:
            # Check if it's a bare python command
            if re.search(r"\bpython(?!3)\s", line):
                self.fail(
                    f"Line {line_num} in code block uses "
                    f"'python' instead of 'python3': {line}"
                )

    def test_consistency_across_readme(self):
        """Test that Python command usage is consistent throughout README."""
        # Count python3 vs python usage
        python3_count = sum(1 for line in self.readme_lines if "python3" in line)
        python_pattern = r"\bpython(?!3)\s"
        python_count = sum(
            1 for line in self.readme_lines if re.search(python_pattern, line)
        )

        # If we have any python3 commands, we shouldn't have bare python commands
        if python3_count > 0:
            self.assertEqual(
                python_count,
                0,
                f"Inconsistent usage: found {python3_count} 'python3' "
                f"and {python_count} 'python' commands",
            )

    def test_installation_section_uses_python3(self):
        """Test that installation section specifically uses python3."""
        in_installation = False
        installation_lines = []

        for i, line in enumerate(self.readme_lines):
            if "## Installation" in line or "## Setup" in line:
                in_installation = True
            elif line.startswith("##") and in_installation:
                in_installation = False
            elif in_installation and "python" in line:
                installation_lines.append((i + 1, line))

        for line_num, line in installation_lines:
            if re.search(r"\bpython(?!3)\s", line):
                self.fail(
                    f"Installation section line {line_num} should use 'python3': {line}"
                )

    def test_examples_section_uses_python3(self):
        """Test that examples section uses python3."""
        in_examples = False
        example_lines = []

        for i, line in enumerate(self.readme_lines):
            if "## Usage" in line or "## Examples" in line or "## Example" in line:
                in_examples = True
            elif line.startswith("##") and in_examples:
                in_examples = False
            elif in_examples and "python" in line:
                example_lines.append((i + 1, line))

        for line_num, line in example_lines:
            if re.search(r"\bpython(?!3)\s", line):
                self.fail(
                    f"Examples section line {line_num} should use 'python3': {line}"
                )


if __name__ == "__main__":
    unittest.main()
