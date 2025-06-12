"""Behave environment setup for integration tests."""

import os
import shutil
import tempfile


def before_scenario(context, scenario):
    """Set up test environment before each scenario."""
    # Create a temporary directory for test files
    context.temp_dir = tempfile.mkdtemp(prefix="obsidian_test_")

    # Add test cleanup flag
    context.cleanup_files = []


def after_scenario(context, scenario):
    """Clean up test environment after each scenario."""
    # Clean up temporary directory
    if hasattr(context, "temp_dir") and os.path.exists(context.temp_dir):
        shutil.rmtree(context.temp_dir)

    # Clean up any unreadable files
    if hasattr(context, "unreadable_file") and context.unreadable_file.exists():
        # Restore permissions before deletion
        if os.name != "nt":  # Not Windows
            try:
                os.chmod(context.unreadable_file, 0o644)
            except OSError:
                pass
