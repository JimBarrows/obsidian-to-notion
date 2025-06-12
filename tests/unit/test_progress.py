"""Unit tests for progress reporting module."""

import unittest
from unittest.mock import MagicMock, patch

from obsidian_to_notion.utils.progress import ProgressReporter


class TestProgressReporter(unittest.TestCase):
    """Test ProgressReporter class."""

    def setUp(self):
        """Set up test fixtures."""
        self.reporter = ProgressReporter()

    def test_init(self):
        """Test ProgressReporter initialization."""
        self.assertIsNone(self.reporter.current_task)
        self.assertIsNone(self.reporter.progress_bar)

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_start_task(self, mock_tqdm):
        """Test starting a task."""
        mock_bar = MagicMock()
        mock_tqdm.return_value = mock_bar

        self.reporter.start_task("Processing files", total=100)

        self.assertEqual(self.reporter.current_task, "Processing files")
        self.assertEqual(self.reporter.progress_bar, mock_bar)
        mock_tqdm.assert_called_once_with(
            desc="Processing files", total=100, unit="items"
        )

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_start_task_custom_unit(self, mock_tqdm):
        """Test starting a task with custom unit."""
        mock_bar = MagicMock()
        mock_tqdm.return_value = mock_bar

        self.reporter.start_task("Uploading", total=50, unit="files")

        mock_tqdm.assert_called_once_with(desc="Uploading", total=50, unit="files")

    def test_update_no_task(self):
        """Test updating when no task is active."""
        # Should not raise error
        self.reporter.update(1)

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_update_with_task(self, mock_tqdm):
        """Test updating progress."""
        mock_bar = MagicMock()
        mock_tqdm.return_value = mock_bar

        self.reporter.start_task("Processing", total=100)
        self.reporter.update(10)

        mock_bar.update.assert_called_once_with(10)

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_update_multiple(self, mock_tqdm):
        """Test multiple progress updates."""
        mock_bar = MagicMock()
        mock_tqdm.return_value = mock_bar

        self.reporter.start_task("Processing", total=100)
        self.reporter.update(10)
        self.reporter.update(20)
        self.reporter.update(30)

        self.assertEqual(mock_bar.update.call_count, 3)

    def test_finish_no_task(self):
        """Test finishing when no task is active."""
        # Should not raise error
        self.reporter.finish()

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_finish_with_task(self, mock_tqdm):
        """Test finishing a task."""
        mock_bar = MagicMock()
        mock_tqdm.return_value = mock_bar

        self.reporter.start_task("Processing", total=100)
        self.reporter.finish()

        mock_bar.close.assert_called_once()
        self.assertIsNone(self.reporter.current_task)
        self.assertIsNone(self.reporter.progress_bar)

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_set_description_no_task(self, mock_tqdm):
        """Test setting description when no task is active."""
        # Should not raise error
        self.reporter.set_description("New description")

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_set_description_with_task(self, mock_tqdm):
        """Test setting description."""
        mock_bar = MagicMock()
        mock_tqdm.return_value = mock_bar

        self.reporter.start_task("Processing", total=100)
        self.reporter.set_description("Processing file.md")

        mock_bar.set_description.assert_called_once_with("Processing file.md")

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_start_nested_task(self, mock_tqdm):
        """Test starting a nested task."""
        mock_bar = MagicMock()
        mock_tqdm.return_value = mock_bar

        nested_bar = self.reporter.start_nested_task("Sub-task", total=10)

        self.assertIsNotNone(nested_bar)
        mock_tqdm.assert_called_with(
            desc="Sub-task", total=10, unit="items", leave=False
        )

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_context_manager(self, mock_tqdm):
        """Test using as context manager."""
        mock_bar = MagicMock()
        mock_tqdm.return_value = mock_bar

        with self.reporter.task("Processing", total=100) as progress:
            self.assertEqual(progress, self.reporter)
            self.assertEqual(self.reporter.current_task, "Processing")
            self.assertIsNotNone(self.reporter.progress_bar)

        # Should be closed after context
        mock_bar.close.assert_called_once()
        self.assertIsNone(self.reporter.current_task)
        self.assertIsNone(self.reporter.progress_bar)

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_context_manager_with_exception(self, mock_tqdm):
        """Test context manager handles exceptions."""
        mock_bar = MagicMock()
        mock_tqdm.return_value = mock_bar

        try:
            with self.reporter.task("Processing", total=100):
                raise ValueError("Test error")
        except ValueError:
            pass

        # Should still close the bar
        mock_bar.close.assert_called_once()
        self.assertIsNone(self.reporter.current_task)
        self.assertIsNone(self.reporter.progress_bar)

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_multiple_tasks(self, mock_tqdm):
        """Test handling multiple sequential tasks."""
        mock_bar1 = MagicMock()
        mock_bar2 = MagicMock()
        mock_tqdm.side_effect = [mock_bar1, mock_bar2]

        # First task
        self.reporter.start_task("Task 1", total=50)
        self.reporter.update(50)
        self.reporter.finish()

        # Second task
        self.reporter.start_task("Task 2", total=100)
        self.reporter.update(100)
        self.reporter.finish()

        # Both bars should be closed
        mock_bar1.close.assert_called_once()
        mock_bar2.close.assert_called_once()

    def test_report_summary(self):
        """Test report_summary method."""
        summary = {
            "processed": 100,
            "failed": 5,
            "skipped": 10,
        }

        # Should not raise error
        self.reporter.report_summary(summary)

    def test_report_error(self):
        """Test report_error method."""
        # Should not raise error
        self.reporter.report_error("file.md", "Error processing file")


if __name__ == "__main__":
    unittest.main()
