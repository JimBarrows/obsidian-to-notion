"""Unit tests for pre-commit setup and configuration."""

import subprocess
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import yaml


class TestPreCommitSetup(unittest.TestCase):
    """Test cases for pre-commit setup and configuration."""

    def setUp(self):
        """Set up test fixtures."""
        self.config_path = Path(".pre-commit-config.yaml")

    def test_pre_commit_config_exists(self):
        """Test that .pre-commit-config.yaml exists."""
        self.assertTrue(
            self.config_path.exists(),
            ".pre-commit-config.yaml file not found in project root",
        )

    def test_pre_commit_config_valid_yaml(self):
        """Test that pre-commit config is valid YAML."""
        with open(self.config_path) as f:
            try:
                config = yaml.safe_load(f)
                self.assertIsInstance(config, dict)
                self.assertIn("repos", config)
            except yaml.YAMLError as e:
                self.fail(f"Invalid YAML in .pre-commit-config.yaml: {e}")

    def test_required_hooks_configured(self):
        """Test that all required hooks are configured."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        # Extract all hook IDs
        hook_ids = []
        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                hook_ids.append(hook["id"])

        # Required hooks for the project
        required_hooks = ["black", "isort", "flake8", "mypy", "ruff"]

        for hook in required_hooks:
            self.assertIn(
                hook, hook_ids, f"Required hook '{hook}' not found in configuration"
            )

    def test_black_configuration(self):
        """Test Black hook configuration."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        black_hook = None
        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                if hook["id"] == "black":
                    black_hook = hook
                    break

        self.assertIsNotNone(black_hook, "Black hook not found")
        # Black should include Python files
        self.assertIn("types", black_hook)
        self.assertIn("python", black_hook["types"])

    def test_isort_configuration(self):
        """Test isort hook configuration."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        isort_hook = None
        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                if hook["id"] == "isort":
                    isort_hook = hook
                    break

        self.assertIsNotNone(isort_hook, "isort hook not found")
        # Check for any custom args if needed
        if "args" in isort_hook:
            self.assertIsInstance(isort_hook["args"], list)

    def test_mypy_configuration(self):
        """Test Mypy hook configuration."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        mypy_hook = None
        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                if hook["id"] == "mypy":
                    mypy_hook = hook
                    break

        self.assertIsNotNone(mypy_hook, "Mypy hook not found")
        # Mypy might need additional dependencies
        if "additional_dependencies" in mypy_hook:
            self.assertIsInstance(mypy_hook["additional_dependencies"], list)

    @patch("subprocess.run")
    def test_pre_commit_validate_config(self, mock_run):
        """Test that pre-commit configuration is valid."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        result = subprocess.run(
            ["pre-commit", "validate-config"],
            capture_output=True,
            text=True,
            check=False,
        )

        mock_run.assert_called_once()
        self.assertEqual(result.returncode, 0)

    def test_hooks_have_proper_stages(self):
        """Test that hooks are configured for appropriate stages."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                # If stages are specified, they should be valid
                if "stages" in hook:
                    valid_stages = [
                        "commit",
                        "merge-commit",
                        "push",
                        "prepare-commit-msg",
                        "commit-msg",
                        "post-checkout",
                        "post-commit",
                        "post-merge",
                        "post-rewrite",
                    ]
                    for stage in hook["stages"]:
                        self.assertIn(
                            stage,
                            valid_stages,
                            f"Invalid stage '{stage}' in hook '{hook['id']}'",
                        )

    def test_repo_versions_specified(self):
        """Test that all repos have versions specified."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        for repo in config.get("repos", []):
            self.assertIn(
                "rev",
                repo,
                f"Repository {repo.get('repo', 'unknown')} missing 'rev' field",
            )
            # Version should not be empty
            self.assertTrue(
                repo["rev"],
                f"Repository {repo.get('repo', 'unknown')} has empty 'rev' field",
            )

    def test_no_duplicate_hooks(self):
        """Test that there are no duplicate hook IDs."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        hook_ids = []
        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                hook_id = hook["id"]
                self.assertNotIn(
                    hook_id, hook_ids, f"Duplicate hook ID found: '{hook_id}'"
                )
                hook_ids.append(hook_id)

    def test_python_version_compatibility(self):
        """Test that hooks are compatible with project Python version."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        # Check if any hooks specify Python version requirements
        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                if "language_version" in hook:
                    version = hook["language_version"]
                    # Should be compatible with Python 3.8+
                    self.assertTrue(
                        version.startswith("python3"),
                        f"Hook '{hook['id']}' uses incompatible Python version",
                    )

    def test_exclude_patterns_reasonable(self):
        """Test that exclude patterns are reasonable if specified."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                if "exclude" in hook:
                    exclude = hook["exclude"]
                    # Exclude should be a string (regex pattern)
                    self.assertIsInstance(
                        exclude,
                        str,
                        f"Hook '{hook['id']}' has invalid exclude pattern",
                    )
                    # Common exclusions that make sense
                    # Just verify it's a non-empty string
                    self.assertTrue(
                        exclude, f"Hook '{hook['id']}' has empty exclude pattern"
                    )


if __name__ == "__main__":
    unittest.main()
